import pandas as pd
from unittest.mock import patch, MagicMock
from django.test import SimpleTestCase

from app.management.commands.load_data_csv_raw import Command
from app.models import Customer, Order

MOD = "app.management.commands.load_data_csv_raw"


def make_cmd() -> Command:
    cmd = Command()
    cmd.stdout = MagicMock()
    cmd.style = MagicMock()
    cmd.style.SUCCESS = lambda x: x
    cmd.style.WARNING = lambda x: x
    return cmd


def make_instance(model_class, **attrs):
    """
    Cree une vraie instance du modele Django SANS toucher la DB.
    Necessaire pour les FK : Django verifie isinstance() a l'assignation
    => un MagicMock est rejete avec 'Cannot assign MagicMock'.
    """
    obj = model_class.__new__(model_class)
    obj.__dict__.update({"_state": MagicMock()})
    for key, val in attrs.items():
        setattr(obj, key, val)
    return obj


class BaseImportTest(SimpleTestCase):

    def assert_bulk_called_with_n(self, mock_bulk, n):
        self.assertEqual(len(mock_bulk.call_args.args[0]), n)

    def assert_ignore_conflicts(self, mock_bulk):
        self.assertTrue(mock_bulk.call_args.kwargs["ignore_conflicts"])


# =====================================================
# HANDLE
# =====================================================

class TestHandle(BaseImportTest):

    @patch(f"{MOD}.transaction.atomic")
    @patch.object(Command, "review_import")
    @patch.object(Command, "import_payments")
    @patch.object(Command, "import_order_items")
    @patch.object(Command, "import_orders")
    @patch.object(Command, "import_sellers")
    @patch.object(Command, "import_customers")
    @patch.object(Command, "import_products")
    @patch.object(Command, "import_categories")
    @patch.object(Command, "import_geolocations")
    def test_handle_calls_all_imports(
            self,
            mock_geo, mock_categories, mock_products, mock_customers,
            mock_sellers, mock_orders, mock_order_items, mock_payments,
            mock_reviews,
            mock_atomic,
    ):
        make_cmd().handle(
            geolocation="f.csv", category="f.csv", product="f.csv",
            customer="f.csv", seller="f.csv", order="f.csv",
            order_item="f.csv", payment="f.csv", review="f.csv",
        )
        for mock in [mock_geo, mock_categories, mock_products, mock_customers,
                     mock_sellers, mock_orders, mock_order_items,
                     mock_payments, mock_reviews]:
            mock.assert_called_once()

    @patch(f"{MOD}.transaction.atomic")
    @patch.object(Command, "review_import")
    @patch.object(Command, "import_payments")
    @patch.object(Command, "import_order_items")
    @patch.object(Command, "import_orders")
    @patch.object(Command, "import_sellers")
    @patch.object(Command, "import_customers")
    @patch.object(Command, "import_products")
    @patch.object(Command, "import_categories")
    @patch.object(Command, "import_geolocations",
                  side_effect=RuntimeError("CSV introuvable"))
    def test_handle_exception_remonte(
        self,
        mock_geo, mock_categories, mock_products, mock_customers,
        mock_sellers, mock_orders, mock_order_items, mock_payments,
        mock_reviews,
        mock_atomic,
    ):
        with self.assertRaises(RuntimeError) as ctx:
            make_cmd().handle(
                geolocation="f.csv", category="f.csv", product="f.csv",
                customer="f.csv", seller="f.csv", order="f.csv",
                order_item="f.csv", payment="f.csv", review="f.csv",
            )
        self.assertIn("CSV introuvable", str(ctx.exception))


# =====================================================
# GEOLOCATIONS
# =====================================================

@patch(f"{MOD}.Geolocation.objects.bulk_create")
@patch(f"{MOD}.pd.read_csv")
class TestImportGeolocations(BaseImportTest):

    def test_nominal(self, mock_csv, mock_bulk):
        mock_csv.return_value = pd.DataFrame({
            "geolocation_zip_code_prefix": ["01001", "01002"],
            "geolocation_lat": [-23.5, -23.6],
            "geolocation_lng": [-46.6, -46.7],
            "geolocation_city": ["sp", "campinas"],
            "geolocation_state": ["SP", "SP"],
        })
        mock_bulk.return_value = []
        make_cmd().import_geolocations("fake.csv")
        mock_bulk.assert_called_once()
        self.assert_bulk_called_with_n(mock_bulk, 2)
        self.assert_ignore_conflicts(mock_bulk)

    def test_empty_file(self, mock_csv, mock_bulk):
        mock_csv.return_value = pd.DataFrame({
            "geolocation_zip_code_prefix": [], "geolocation_lat": [],
            "geolocation_lng": [], "geolocation_city": [], "geolocation_state": [],
        })
        mock_bulk.return_value = []
        make_cmd().import_geolocations("fake.csv")
        self.assert_bulk_called_with_n(mock_bulk, 0)


# =====================================================
# CUSTOMERS
# FIX : Geolocation.objects.only manquait => touchait la vraie DB
# =====================================================

@patch(f"{MOD}.Customer.objects.bulk_create")
@patch(f"{MOD}.Geolocation.objects.only")
@patch(f"{MOD}.pd.read_csv")
class TestImportCustomers(BaseImportTest):

    def test_nominal(self, mock_csv, mock_geo_only, mock_bulk):
        mock_geo_only.return_value = []
        mock_csv.return_value = pd.DataFrame({
            "customer_id":          ["1", "2"],
            "customer_first_name":  ["Alice", "Bob"],
            "customer_last_name":   ["A", "B"],
            "customer_zip_code_prefix": ["01001", "01002"],
            "customer_city":        ["sp", "rio"],
            "customer_state":       ["SP", "RJ"],
            "customer_address":     ["Rua X", "Av Y"],
        })
        mock_bulk.return_value = []

        make_cmd().import_customers("fake.csv")

        mock_bulk.assert_called_once()
        self.assert_bulk_called_with_n(mock_bulk, 2)
        self.assert_ignore_conflicts(mock_bulk)

    def test_empty_file(self, mock_csv, mock_geo_only, mock_bulk):
        mock_geo_only.return_value = []
        mock_csv.return_value = pd.DataFrame({
            "customer_id": [], "customer_unique_id": [],
            "customer_zip_code_prefix": [], "customer_city": [], "customer_state": [],
        })
        mock_bulk.return_value = []
        make_cmd().import_customers("fake.csv")
        self.assert_bulk_called_with_n(mock_bulk, 0)


# =====================================================
# ORDERS
# FIX 1 : parse_datetime_column.side_effect dans TOUS les tests
# FIX 2 : make_instance(Customer) pour passer isinstance()
# FIX 3 : verifier customer_id (pas .customer qui fait une requete DB)
# =====================================================

@patch(f"{MOD}.Order.objects.bulk_create")
@patch(f"{MOD}.parse_datetime_column")
@patch(f"{MOD}.pd.read_csv")
@patch(f"{MOD}.Customer.objects.only")
class TestImportOrders(BaseImportTest):

    ORDER_CSV = {
        "order_id": ["1"], "customer_id": ["1"], "order_status": ["delivered"],
        "order_purchase_timestamp": ["2024-01-01 10:00:00"],
        "order_approved_at": ["2024-01-01 11:00:00"],
        "order_delivered_carrier_date": ["2024-01-02 10:00:00"],
        "order_delivered_customer_date": ["2024-01-03 10:00:00"],
        "order_estimated_delivery_date": ["2024-01-04 10:00:00"],
    }

    def _no_op_dt(self, mock_parse_dt):
        # Sans ca, mock retourne MagicMock a la place de la colonne
        # => exception catchee silencieusement => bulk_create recoit []
        mock_parse_dt.side_effect = lambda frame, col: frame[col]

    def test_nominal(self, mock_customers, mock_csv, mock_parse_dt, mock_bulk):
        self._no_op_dt(mock_parse_dt)
        mock_customers.return_value = [make_instance(Customer, customer_id="1")]
        mock_csv.return_value = pd.DataFrame(self.ORDER_CSV)
        mock_bulk.return_value = []
        make_cmd().import_orders("fake.csv")
        mock_bulk.assert_called_once()
        self.assert_bulk_called_with_n(mock_bulk, 1)
        self.assert_ignore_conflicts(mock_bulk)

    def test_customer_fk_lie(self, mock_customers, mock_csv, mock_parse_dt, mock_bulk):
        self._no_op_dt(mock_parse_dt)
        fake = make_instance(Customer, customer_id="1")
        mock_customers.return_value = [fake]
        mock_csv.return_value = pd.DataFrame(self.ORDER_CSV)
        mock_bulk.return_value = []
        make_cmd().import_orders("fake.csv")
        obj = mock_bulk.call_args.args[0][0]
        self.assertEqual(obj.customer_id, fake.pk)

    def test_customer_inconnu_est_none(self, mock_customers, mock_csv,
                                       mock_parse_dt, mock_bulk):
        self._no_op_dt(mock_parse_dt)
        mock_customers.return_value = []
        mock_csv.return_value = pd.DataFrame({**self.ORDER_CSV, "customer_id": ["inconnu"]})
        mock_bulk.return_value = []
        make_cmd().import_orders("fake.csv")
        obj = mock_bulk.call_args.args[0][0]
        self.assertIsNone(obj.customer_id)

    def test_parse_datetime_appele_5_fois(self, mock_customers, mock_csv,
                                          mock_parse_dt, mock_bulk):
        self._no_op_dt(mock_parse_dt)
        mock_customers.return_value = []
        mock_csv.return_value = pd.DataFrame(self.ORDER_CSV)
        mock_bulk.return_value = []
        make_cmd().import_orders("fake.csv")
        self.assertEqual(mock_parse_dt.call_count, 5)


# =====================================================
# PRODUCTS
# FIX : Category.objects.only manquait => touchait la vraie DB
# =====================================================

@patch(f"{MOD}.Product.objects.bulk_create")
@patch(f"{MOD}.Category.objects.only")
@patch(f"{MOD}.pd.read_csv")
class TestImportProducts(BaseImportTest):

    def test_nominal(self, mock_csv, mock_cat_only, mock_bulk):
        mock_cat_only.return_value = []
        mock_csv.return_value = pd.DataFrame({
            "product_id": ["1"], "product_category_name": ["books"],
            "product_name_lenght": [10],         # faute intentionnelle Olist
            "product_description_lenght": [100], # idem
            "product_photos_qty": [2], "product_weight_g": [500],
            "product_length_cm": [20], "product_height_cm": [5], "product_width_cm": [15],
        })
        mock_bulk.return_value = []
        make_cmd().import_products("fake.csv")
        mock_bulk.assert_called_once()
        self.assert_bulk_called_with_n(mock_bulk, 1)
        self.assert_ignore_conflicts(mock_bulk)

    def test_empty_file(self, mock_csv, mock_cat_only, mock_bulk):
        mock_cat_only.return_value = []
        mock_csv.return_value = pd.DataFrame({
            "product_id": [], "product_category_name": [],
            "product_name_lenght": [], "product_description_lenght": [],
            "product_photos_qty": [], "product_weight_g": [],
            "product_length_cm": [], "product_height_cm": [], "product_width_cm": [],
        })
        mock_bulk.return_value = []
        make_cmd().import_products("fake.csv")
        self.assert_bulk_called_with_n(mock_bulk, 0)


# =====================================================
# PAYMENTS
# FIX : make_instance(Order) pour passer isinstance()
# =====================================================

@patch(f"{MOD}.Payment.objects.bulk_create")
@patch(f"{MOD}.pd.read_csv")
@patch(f"{MOD}.Order.objects.only")
class TestImportPayments(BaseImportTest):

    def test_nominal(self, mock_orders, mock_csv, mock_bulk):
        mock_orders.return_value = [make_instance(Order, order_id="1")]
        mock_csv.return_value = pd.DataFrame({
            "order_id": ["1"], "payment_sequential": [1],
            "payment_type": ["credit_card"], "payment_installments": [2],
            "payment_value": [150.0],
        })
        mock_bulk.return_value = []
        make_cmd().import_payments("fake.csv")
        mock_bulk.assert_called_once()
        self.assert_bulk_called_with_n(mock_bulk, 1)
        self.assert_ignore_conflicts(mock_bulk)

    def test_order_fk_lie(self, mock_orders, mock_csv, mock_bulk):
        fake = make_instance(Order, order_id="1")
        mock_orders.return_value = [fake]
        mock_csv.return_value = pd.DataFrame({
            "order_id": ["1"], "payment_sequential": [1],
            "payment_type": ["boleto"], "payment_installments": [1], "payment_value": [75.0],
        })
        mock_bulk.return_value = []
        make_cmd().import_payments("fake.csv")
        obj = mock_bulk.call_args.args[0][0]
        self.assertEqual(obj.order_id, fake.pk)

    def test_order_inconnu_est_none(self, mock_orders, mock_csv, mock_bulk):
        mock_orders.return_value = []
        mock_csv.return_value = pd.DataFrame({
            "order_id": ["ghost"], "payment_sequential": [1],
            "payment_type": ["boleto"], "payment_installments": [1], "payment_value": [50.0],
        })
        mock_bulk.return_value = []
        make_cmd().import_payments("fake.csv")
        obj = mock_bulk.call_args.args[0][0]
        self.assertIsNone(obj.order_id)