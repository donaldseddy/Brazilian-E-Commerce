"""
tests/test_load_olist_data.py

Tests unitaires pour la commande load_olist_data.

Architecture :
  - Tests des utilitaires purs (normalize_uuid, to_str, to_int, parse_dt)
  - Tests des _build_* (logique métier sans I/O DB)
  - Tests d'intégration des importers (avec DB via TestCase)

Conventions :
  - Fixtures minimales créées dans setUp()
  - Chaque test est indépendant (pas d'ordre requis)
  - Noms : test_<methode>_<scenario>
"""

from __future__ import annotations

import uuid
from io import StringIO
from unittest.mock import MagicMock, patch

from django.test import TestCase

from app.management.commands.load_olist_data import (
    Command,
    ImportStats,
    normalize_uuid,
    parse_dt,
    to_int,
    to_str,
)
from app.models import (
    Category,
    Customer,
    Geolocation,
    Order,
    OrderItem,
    Payment,
    Product,
    Review,
    Seller,
    User,
)


# ─────────────────────────────────────────────────────────────────────────────
# UTILITAIRES PURS  (pas de DB)
# ─────────────────────────────────────────────────────────────────────────────

class TestNormalizeUuid(TestCase):
    """normalize_uuid : hex 32 chars → uuid.UUID"""

    def test_valid_hex_32(self):
        result = normalize_uuid("06b8999e2fba1a1fbc88172c00ba8bc7")
        self.assertIsInstance(result, uuid.UUID)
        self.assertEqual(str(result), "06b8999e-2fba-1a1f-bc88-172c00ba8bc7")

    def test_valid_with_dashes(self):
        value  = "06b8999e-2fba-1a1f-bc88-172c00ba8bc7"
        result = normalize_uuid(value)
        self.assertIsInstance(result, uuid.UUID)

    def test_none_returns_none(self):
        self.assertIsNone(normalize_uuid(None))

    def test_empty_string_returns_none(self):
        self.assertIsNone(normalize_uuid(""))

    def test_invalid_string_returns_none(self):
        self.assertIsNone(normalize_uuid("not-a-uuid"))

    def test_uuid_object_passthrough(self):
        uid    = uuid.uuid4()
        result = normalize_uuid(str(uid))
        self.assertEqual(result, uid)


class TestToStr(TestCase):
    """to_str : NaN / None → default, sinon str strippé"""

    def test_normal_string(self):
        self.assertEqual(to_str("  hello  "), "hello")

    def test_none_returns_default(self):
        self.assertEqual(to_str(None), "")
        self.assertEqual(to_str(None, "fallback"), "fallback")

    def test_nan_string_returns_default(self):
        self.assertEqual(to_str("nan"), "")
        self.assertEqual(to_str("NaN"), "")

    def test_empty_string_returns_default(self):
        self.assertEqual(to_str(""), "")

    def test_numeric_value(self):
        self.assertEqual(to_str(42), "42")


class TestToInt(TestCase):
    """to_int : conversions et cas limites"""

    def test_integer_string(self):
        self.assertEqual(to_int("5"), 5)

    def test_float_string(self):
        self.assertEqual(to_int("3.7"), 3)

    def test_none_returns_none(self):
        self.assertIsNone(to_int(None))

    def test_empty_string_returns_none(self):
        self.assertIsNone(to_int(""))

    def test_invalid_string_returns_none(self):
        self.assertIsNone(to_int("abc"))


class TestParseDt(TestCase):
    """parse_dt : string datetime → datetime aware ou None"""

    def test_valid_datetime_string(self):
        result = parse_dt("2017-10-02 10:56:33")
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.tzinfo)

    def test_none_returns_none(self):
        self.assertIsNone(parse_dt(None))

    def test_empty_string_returns_none(self):
        self.assertIsNone(parse_dt(""))

    def test_invalid_string_returns_none(self):
        self.assertIsNone(parse_dt("not-a-date"))


class TestImportStats(TestCase):
    """ImportStats : suivi cohérent des compteurs"""

    def test_initial_state(self):
        stats = ImportStats(entity="Test", total=100)
        self.assertEqual(stats.imported, 0)
        self.assertEqual(stats.failed,   0)
        self.assertEqual(stats.errors,   [])

    def test_record_error_increments_failed(self):
        stats = ImportStats(entity="Test", total=10)
        stats.record_error("something went wrong")
        self.assertEqual(stats.failed, 1)
        self.assertIn("something went wrong", stats.errors)

    def test_summary_format(self):
        stats = ImportStats(entity="Product", total=100, imported=95, skipped=3, failed=2)
        s = stats.summary()
        self.assertIn("Product", s)
        self.assertIn("95",      s)
        self.assertIn("2",       s)


# ─────────────────────────────────────────────────────────────────────────────
# _BUILD_* — logique métier (sans I/O DB, mocks simples)
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildGeolocation(TestCase):

    def _row(self, **kwargs):
        defaults = dict(
            geolocation_zip_code_prefix="14409",
            geolocation_lat="-20.5",
            geolocation_lng="-47.4",
            geolocation_city="franca",
            geolocation_state="SP",
        )
        defaults.update(kwargs)
        return MagicMock(**defaults)

    def test_valid_row_returns_geolocation(self):
        stats  = ImportStats(entity="Geo", total=1)
        result = Command._build_geolocation(self._row(), stats)
        self.assertIsNotNone(result)
        self.assertIsInstance(result, Geolocation)
        self.assertEqual(result.geolocation_zip_code_prefix, "14409")

    def test_zip_code_padded_to_5_chars(self):
        stats  = ImportStats(entity="Geo", total=1)
        result = Command._build_geolocation(self._row(geolocation_zip_code_prefix="123"), stats)
        self.assertEqual(result.geolocation_zip_code_prefix, "00123")

    def test_invalid_lat_records_error(self):
        stats  = ImportStats(entity="Geo", total=1)
        result = Command._build_geolocation(
            self._row(geolocation_lat="not_a_float"), stats
        )
        self.assertIsNone(result)
        self.assertEqual(stats.failed, 1)


class TestBuildCategory(TestCase):

    def _row(self, name="perfumaria", english="health_beauty"):
        return MagicMock(
            product_category_name=name,
            product_category_name_english=english,
        )

    def test_valid_row_returns_category(self):
        stats  = ImportStats(entity="Cat", total=1)
        result = Command._build_category(self._row(), stats)
        self.assertIsNotNone(result)
        self.assertEqual(result.product_category_name, "perfumaria")

    def test_empty_name_records_error(self):
        stats  = ImportStats(entity="Cat", total=1)
        result = Command._build_category(self._row(name=""), stats)
        self.assertIsNone(result)
        self.assertEqual(stats.failed, 1)


class TestBuildProduct(TestCase):

    def _row(self, **kwargs):
        defaults = dict(
            product_id           = "1e9e8ef04dbcff4541ed26657ea517e5",
            product_category_name= "perfumaria",
            product_name_lenght  = "40",
            product_description_lenght = "287",
            product_photos_qty   = "1",
            product_weight_g     = "225",
            product_length_cm    = "16",
            product_height_cm    = "10",
            product_width_cm     = "14",
        )
        defaults.update(kwargs)
        return MagicMock(**defaults)

    def test_valid_row_returns_product(self):
        stats  = ImportStats(entity="Product", total=1)
        result = Command._build_product(self._row(), {}, stats)
        self.assertIsNotNone(result)
        self.assertEqual(result.product_weight_g, 225)

    def test_invalid_uuid_records_error(self):
        stats  = ImportStats(entity="Product", total=1)
        result = Command._build_product(self._row(product_id="bad"), {}, stats)
        self.assertIsNone(result)
        self.assertEqual(stats.failed, 1)

    def test_missing_weight_records_error(self):
        stats  = ImportStats(entity="Product", total=1)
        result = Command._build_product(self._row(product_weight_g=""), {}, stats)
        self.assertIsNone(result)
        self.assertEqual(stats.failed, 1)

    def test_category_assigned_when_found(self):
        cat   = MagicMock()
        stats = ImportStats(entity="Product", total=1)
        result = Command._build_product(self._row(), {"perfumaria": cat}, stats)
        self.assertEqual(result.category, cat)

    def test_category_none_when_not_found(self):
        stats  = ImportStats(entity="Product", total=1)
        result = Command._build_product(self._row(), {}, stats)
        self.assertIsNone(result.category)


class TestBuildCustomerPair(TestCase):

    def _row(self, **kwargs):
        defaults = dict(
            customer_id              = "06b8999e2fba1a1fbc88172c00ba8bc7",
            customer_zip_code_prefix = "14409",
            customer_city            = "franca",
            customer_state           = "SP",
            customer_first_name      = "Ana",
            customer_last_name       = "Silva",
            customer_address         = "Rua Minas Gerais, 919",
        )
        defaults.update(kwargs)
        return MagicMock(**defaults)

    def test_valid_row_returns_tuple(self):
        stats  = ImportStats(entity="Customer", total=1)
        result = Command._build_customer_pair(self._row(), {}, stats)
        self.assertIsNotNone(result)
        user, cid = result
        self.assertIsInstance(user, User)
        self.assertIsInstance(cid,  uuid.UUID)

    def test_user_fields_populated(self):
        stats  = ImportStats(entity="Customer", total=1)
        user, _ = Command._build_customer_pair(self._row(), {}, stats)
        self.assertEqual(user.first_name, "Ana")
        self.assertEqual(user.last_name,  "Silva")
        self.assertEqual(user.role,       User.ROLE_CUSTOMER)
        self.assertFalse(user.is_active)

    def test_city_title_cased(self):
        stats   = ImportStats(entity="Customer", total=1)
        user, _ = Command._build_customer_pair(self._row(customer_city="sao paulo"), {}, stats)
        self.assertEqual(user.city, "Sao Paulo")

    def test_state_uppercased(self):
        stats   = ImportStats(entity="Customer", total=1)
        user, _ = Command._build_customer_pair(self._row(customer_state="sp"), {}, stats)
        self.assertEqual(user.state, "SP")

    def test_invalid_uuid_records_error(self):
        stats  = ImportStats(entity="Customer", total=1)
        result = Command._build_customer_pair(self._row(customer_id="bad"), {}, stats)
        self.assertIsNone(result)
        self.assertEqual(stats.failed, 1)



class TestBuildSellerPair(TestCase):

    def _row(self, **kwargs):
        defaults = dict(
            seller_id              = "3442f8959a84dea7ee197c632cb2df15",
            seller_zip_code_prefix = "13023",
            seller_city            = "campinas",
            seller_state           = "SP",
            seller_first_name      = "Renata",
            seller_last_name       = "Silva",
            seller_full_address    = "Av. Atlântica, 8571",
        )
        defaults.update(kwargs)
        return MagicMock(**defaults)

    def test_valid_row_returns_tuple(self):
        stats  = ImportStats(entity="Seller", total=1)
        result = Command._build_seller_pair(self._row(), {}, stats)
        self.assertIsNotNone(result)
        user, sid = result
        self.assertIsInstance(user, User)
        self.assertIsInstance(sid,  uuid.UUID)
        self.assertEqual(user.role, User.ROLE_SELLER)

    def test_invalid_uuid_records_error(self):
        stats  = ImportStats(entity="Seller", total=1)
        result = Command._build_seller_pair(self._row(seller_id="xxx"), {}, stats)
        self.assertIsNone(result)
        self.assertEqual(stats.failed, 1)

    def test_address_from_full_address(self):
        stats   = ImportStats(entity="Seller", total=1)
        user, _ = Command._build_seller_pair(self._row(), {}, stats)
        self.assertEqual(user.address, "Av. Atlântica, 8571")


class TestBuildOrder(TestCase):

    def _row(self, **kwargs):
        defaults = dict(
            order_id                      = "e481f51cbdc54678b7cc49136f2d6af7",
            customer_id                   = "9ef432eb6251297304e76186b10a928d",
            order_status                  = "delivered",
            order_purchase_timestamp      = "2017-10-02 10:56:33",
            order_approved_at             = "2017-10-02 11:07:15",
            order_delivered_carrier_date  = "",
            order_delivered_customer_date = "",
            order_estimated_delivery_date = "2017-10-18 00:00:00",
        )
        defaults.update(kwargs)
        return MagicMock(**defaults)

    def _customer(self):
        cid = normalize_uuid("9ef432eb6251297304e76186b10a928d")
        return {str(cid): MagicMock()}

    def test_valid_row_returns_order(self):
        stats  = ImportStats(entity="Order", total=1)
        result = Command._build_order(self._row(), self._customer(), stats)
        self.assertIsNotNone(result)
        self.assertEqual(result.order_status, "delivered")

    def test_invalid_order_uuid_records_error(self):
        stats  = ImportStats(entity="Order", total=1)
        result = Command._build_order(self._row(order_id="bad"), self._customer(), stats)
        self.assertIsNone(result)
        self.assertEqual(stats.failed, 1)

    def test_unknown_customer_records_error(self):
        stats  = ImportStats(entity="Order", total=1)
        result = Command._build_order(self._row(), {}, stats)
        self.assertIsNone(result)
        self.assertEqual(stats.failed, 1)

    def test_optional_dates_can_be_empty(self):
        stats  = ImportStats(entity="Order", total=1)
        result = Command._build_order(self._row(), self._customer(), stats)
        self.assertIsNone(result.order_delivered_carrier_date)
        self.assertIsNone(result.order_delivered_customer_date)

    def test_purchase_timestamp_is_not_none(self):
        """order_purchase_timestamp ne peut pas être NULL → fallback timezone.now()"""
        stats  = ImportStats(entity="Order", total=1)
        result = Command._build_order(
            self._row(order_purchase_timestamp=""), self._customer(), stats
        )
        # Doit quand même renvoyer un objet (fallback timezone.now())
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.order_purchase_timestamp)


class TestBuildOrderItem(TestCase):

    def _row(self, **kwargs):
        defaults = dict(
            order_id       = "00010242fe8c5a6d1ba2dd792cb16214",
            order_item_id  = "1",
            product_id     = "4244733e06e7ecb4970a6e2683c13e61",
            seller_id      = "48436dade18ac8b2bce089ec2a041202",
            shipping_limit_date = "2017-09-19 09:45:35",
            price          = "58.90",
            freight_value  = "13.29",
        )
        defaults.update(kwargs)
        return MagicMock(**defaults)

    def _make_dicts(self):
        oid = str(normalize_uuid("00010242fe8c5a6d1ba2dd792cb16214"))
        pid = str(normalize_uuid("4244733e06e7ecb4970a6e2683c13e61"))
        sid = str(normalize_uuid("48436dade18ac8b2bce089ec2a041202"))
        return (
            {oid: MagicMock()},
            {pid: MagicMock()},
            {sid: MagicMock()},
        )

    def test_valid_row_returns_order_item(self):
        stats          = ImportStats(entity="OI", total=1)
        orders, prods, sellers = self._make_dicts()
        result = Command._build_order_item(self._row(), orders, prods, sellers, stats)
        self.assertIsNotNone(result)
        # Rupture clé : order_item_id CSV → order_item_sequence_number
        self.assertEqual(result.order_item_sequence_number, 1)

    def test_sequence_number_is_int(self):
        """order_item_id CSV (1,2,3...) doit atterrir dans order_item_sequence_number en int."""
        stats          = ImportStats(entity="OI", total=1)
        orders, prods, sellers = self._make_dicts()
        result = Command._build_order_item(self._row(order_item_id="3"), orders, prods, sellers, stats)
        self.assertEqual(result.order_item_sequence_number, 3)
        self.assertIsInstance(result.order_item_sequence_number, int)

    def test_missing_order_records_error(self):
        stats  = ImportStats(entity="OI", total=1)
        _, prods, sellers = self._make_dicts()
        result = Command._build_order_item(self._row(), {}, prods, sellers, stats)
        self.assertIsNone(result)
        self.assertEqual(stats.failed, 1)

    def test_missing_product_records_error(self):
        stats  = ImportStats(entity="OI", total=1)
        orders, _, sellers = self._make_dicts()
        result = Command._build_order_item(self._row(), orders, {}, sellers, stats)
        self.assertIsNone(result)

    def test_missing_seller_records_error(self):
        stats  = ImportStats(entity="OI", total=1)
        orders, prods, _ = self._make_dicts()
        result = Command._build_order_item(self._row(), orders, prods, {}, stats)
        self.assertIsNone(result)


class TestBuildPayment(TestCase):
    """
    Rupture critique : payment_timestamp absent du CSV.
    La commande doit injecter timezone.now().
    """

    def _row(self, **kwargs):
        defaults = dict(
            order_id             = "b81ef226f3fe1789b1e8b2acac839d17",
            payment_sequential   = "1",
            payment_type         = "credit_card",
            payment_installments = "8",
            payment_value        = "99.33",
        )
        defaults.update(kwargs)
        return MagicMock(**defaults)

    def _orders(self):
        oid = str(normalize_uuid("b81ef226f3fe1789b1e8b2acac839d17"))
        return {oid: MagicMock()}

    def test_valid_row_returns_payment(self):
        stats  = ImportStats(entity="Payment", total=1)
        result = Command._build_payment(self._row(), self._orders(), stats)
        self.assertIsNotNone(result)
        self.assertEqual(result.payment_type, "credit_card")
        self.assertEqual(result.payment_installments, 8)

    def test_payment_timestamp_always_set(self):
        """payment_timestamp doit toujours être non-None même si absent du CSV."""
        stats  = ImportStats(entity="Payment", total=1)
        result = Command._build_payment(self._row(), self._orders(), stats)
        self.assertIsNotNone(result.payment_timestamp)

    def test_unknown_order_records_error(self):
        stats  = ImportStats(entity="Payment", total=1)
        result = Command._build_payment(self._row(), {}, stats)
        self.assertIsNone(result)
        self.assertEqual(stats.failed, 1)

    def test_invalid_sequential_records_error(self):
        stats  = ImportStats(entity="Payment", total=1)
        result = Command._build_payment(
            self._row(payment_sequential=""), self._orders(), stats
        )
        self.assertIsNone(result)
        self.assertEqual(stats.failed, 1)

    def test_payment_value_as_float(self):
        stats  = ImportStats(entity="Payment", total=1)
        result = Command._build_payment(self._row(), self._orders(), stats)
        self.assertAlmostEqual(float(result.payment_value), 99.33, places=2)


class TestBuildReview(TestCase):
    """
    Rupture : 87 658 / 99 224 reviews ont title/message vides.
    Les deux champs doivent être "" et non None.
    """

    def _row(self, **kwargs):
        defaults = dict(
            review_id               = "7bc2406110b926393aa56f80a40eba40",
            order_id                = "73fc7af87114b39712e6da79b0a377eb",
            review_score            = "4",
            review_comment_title    = "",
            review_comment_message  = "",
            review_creation_date    = "2018-01-18 00:00:00",
            review_answer_timestamp = "2018-01-18 21:46:59",
        )
        defaults.update(kwargs)
        return MagicMock(**defaults)

    def _orders(self):
        oid = str(normalize_uuid("73fc7af87114b39712e6da79b0a377eb"))
        return {oid: MagicMock()}

    def test_valid_row_returns_review(self):
        stats  = ImportStats(entity="Review", total=1)
        result = Command._build_review(self._row(), self._orders(), stats)
        self.assertIsNotNone(result)
        self.assertEqual(result.review_score, 4)

    def test_empty_title_becomes_empty_string_not_none(self):
        """Rupture : NaN/vide → "" pour éviter le NOT NULL constraint."""
        stats  = ImportStats(entity="Review", total=1)
        result = Command._build_review(self._row(), self._orders(), stats)
        self.assertEqual(result.review_comment_title,   "")
        self.assertEqual(result.review_comment_message, "")

    def test_nan_title_becomes_empty_string(self):
        stats  = ImportStats(entity="Review", total=1)
        result = Command._build_review(
            self._row(review_comment_title="nan"), self._orders(), stats
        )
        self.assertEqual(result.review_comment_title, "")

    def test_populated_title_preserved(self):
        stats  = ImportStats(entity="Review", total=1)
        result = Command._build_review(
            self._row(review_comment_title="Excellent produit"), self._orders(), stats
        )
        self.assertEqual(result.review_comment_title, "Excellent produit")

    def test_invalid_uuid_records_error(self):
        stats  = ImportStats(entity="Review", total=1)
        result = Command._build_review(self._row(review_id="bad"), self._orders(), stats)
        self.assertIsNone(result)
        self.assertEqual(stats.failed, 1)

    def test_unknown_order_records_error(self):
        stats  = ImportStats(entity="Review", total=1)
        result = Command._build_review(self._row(), {}, stats)
        self.assertIsNone(result)

    def test_invalid_score_records_error(self):
        stats  = ImportStats(entity="Review", total=1)
        result = Command._build_review(
            self._row(review_score=""), self._orders(), stats
        )
        self.assertIsNone(result)

    def test_answer_timestamp_optional(self):
        stats  = ImportStats(entity="Review", total=1)
        result = Command._build_review(
            self._row(review_answer_timestamp=""), self._orders(), stats
        )
        self.assertIsNotNone(result)
        self.assertIsNone(result.review_answer_timestamp)


# ─────────────────────────────────────────────────────────────────────────────
# INTÉGRATION — avec base de données (TestCase)
# ─────────────────────────────────────────────────────────────────────────────

class TestImportGeolocationsIntegration(TestCase):

    def _csv(self, rows: list[dict]) -> str:
        lines = ["geolocation_zip_code_prefix,geolocation_lat,geolocation_lng,geolocation_city,geolocation_state"]
        for r in rows:
            lines.append(f"{r['zip']},{r['lat']},{r['lng']},{r['city']},{r['state']}")
        return "\n".join(lines)

    def _run(self, csv_content: str) -> ImportStats:
        import tempfile, os
        cmd = Command()
        cmd.batch = 500
        cmd.dry   = False
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            tmp = f.name
        try:
            return cmd.import_geolocations(tmp)
        finally:
            os.unlink(tmp)

    def test_creates_geolocations_in_db(self):
        csv = self._csv([{"zip": "14409", "lat": "-20.5", "lng": "-47.4", "city": "franca", "state": "SP"}])
        stats = self._run(csv)
        self.assertEqual(Geolocation.objects.count(), 1)
        self.assertEqual(stats.imported, 1)

    def test_idempotent_on_rerun(self):
        csv = self._csv([{"zip": "14409", "lat": "-20.5", "lng": "-47.4", "city": "franca", "state": "SP"}])
        self._run(csv)
        self._run(csv)  # deuxième run
        self.assertEqual(Geolocation.objects.count(), 1)  # pas de doublon

    def test_invalid_row_skipped_valid_still_imported(self):
        csv = self._csv([
            {"zip": "14409", "lat": "not_float", "lng": "-47.4", "city": "franca", "state": "SP"},
            {"zip": "01310", "lat": "-23.5",     "lng": "-46.6", "city": "sao paulo", "state": "SP"},
        ])
        stats = self._run(csv)
        self.assertEqual(Geolocation.objects.count(), 1)
        self.assertEqual(stats.failed, 1)


class TestImportCategoriesIntegration(TestCase):

    def test_creates_categories(self):
        import tempfile, os
        csv = "product_category_name,product_category_name_english\nperfumaria,health_beauty\nbrinquedos,toys\n"
        cmd = Command(); cmd.batch = 500; cmd.dry = False
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv); tmp = f.name
        try:
            stats = cmd.import_categories(tmp)
        finally:
            os.unlink(tmp)
        self.assertEqual(Category.objects.count(), 2)
        self.assertEqual(stats.imported, 2)


class TestImportCustomersIntegration(TestCase):
    """
    Test de la rupture principale :
    Customer ne porte plus les données démographiques → User intermédiaire.
    """

    def setUp(self):
        self.geo = Geolocation.objects.create(
            geolocation_zip_code_prefix = "14409",
            geolocation_lat             = -20.5,
            geolocation_lng             = -47.4,
            geolocation_city            = "franca",
            geolocation_state           = "SP",
        )

    def _csv(self, rows: list[dict]) -> str:
        header = "customer_id,customer_unique_id,customer_zip_code_prefix,customer_city,customer_state,customer_first_name,customer_last_name,customer_address"
        lines  = [header]
        for r in rows:
            lines.append(
                f"{r['id']},{r.get('uid',r['id'])},{r['zip']},{r['city']},{r['state']},{r['fn']},{r['ln']},{r.get('addr','')}"
            )
        return "\n".join(lines)

    def _run(self, csv_content: str) -> ImportStats:
        import tempfile, os
        cmd = Command(); cmd.batch = 500; cmd.dry = False
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content); tmp = f.name
        try:
            return cmd.import_customers(tmp)
        finally:
            os.unlink(tmp)

    def test_creates_user_and_customer(self):
        """Chaque ligne CSV doit créer 1 User ET 1 Customer lié."""
        csv   = self._csv([{"id": "06b8999e2fba1a1fbc88172c00ba8bc7", "zip": "14409", "city": "franca", "state": "SP", "fn": "Ana", "ln": "Silva"}])
        stats = self._run(csv)
        self.assertEqual(User.objects.filter(role=User.ROLE_CUSTOMER).count(), 1)
        self.assertEqual(Customer.objects.count(), 1)
        self.assertIsNotNone(Customer.objects.first().user)

    def test_demographic_data_on_user_not_customer(self):
        """Rupture : first_name/last_name/city sont sur User, pas sur Customer."""
        csv = self._csv([{"id": "06b8999e2fba1a1fbc88172c00ba8bc7", "zip": "14409", "city": "franca", "state": "SP", "fn": "Ana", "ln": "Silva"}])
        self._run(csv)
        user = User.objects.get(role=User.ROLE_CUSTOMER)
        self.assertEqual(user.first_name, "Ana")
        self.assertEqual(user.last_name,  "Silva")
        self.assertEqual(user.city,       "Franca")  # title case
        self.assertEqual(user.state,      "SP")

    def test_customer_uuid_matches_csv(self):
        csv = self._csv([{"id": "06b8999e2fba1a1fbc88172c00ba8bc7", "zip": "14409", "city": "franca", "state": "SP", "fn": "Ana", "ln": "Silva"}])
        self._run(csv)
        expected = uuid.UUID("06b8999e2fba1a1fbc88172c00ba8bc7")
        self.assertEqual(Customer.objects.first().customer_id, expected)

    def test_imported_accounts_are_inactive(self):
        """Les comptes importés du CSV ne doivent pas pouvoir se connecter directement."""
        csv = self._csv([{"id": "06b8999e2fba1a1fbc88172c00ba8bc7", "zip": "14409", "city": "franca", "state": "SP", "fn": "Ana", "ln": "Silva"}])
        self._run(csv)
        user = User.objects.get(role=User.ROLE_CUSTOMER)
        self.assertFalse(user.is_active)


class TestImportPaymentsIntegration(TestCase):
    """
    Test de la rupture payment_timestamp.
    """

    def setUp(self):
        # Créer le minimum pour avoir une Order valide
        geo = Geolocation.objects.create(
            geolocation_zip_code_prefix="14409",
            geolocation_lat=-20.5, geolocation_lng=-47.4,
            geolocation_city="franca", geolocation_state="SP",
        )
        user = User.objects.create_user(
            username="test@test.com", email="test@test.com",
            password="x", role=User.ROLE_CUSTOMER,
        )
        self.customer = Customer.objects.create(user=user)
        from django.utils import timezone as tz
        self.order = Order.objects.create(
            order_id                 = uuid.UUID("b81ef226f3fe1789b1e8b2acac839d17"),
            customer                 = self.customer,
            order_status             = "delivered",
            order_purchase_timestamp = tz.now(),
        )

    def _run(self, csv_content: str) -> ImportStats:
        import tempfile, os
        cmd = Command(); cmd.batch = 500; cmd.dry = False
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content); tmp = f.name
        try:
            return cmd.import_payments(tmp)
        finally:
            os.unlink(tmp)

    def test_payment_created_with_timestamp(self):
        """payment_timestamp doit être renseigné même si absent du CSV."""
        csv = "order_id,payment_sequential,payment_type,payment_installments,payment_value\nb81ef226f3fe1789b1e8b2acac839d17,1,credit_card,8,99.33\n"
        self._run(csv)
        payment = Payment.objects.first()
        self.assertIsNotNone(payment)
        self.assertIsNotNone(payment.payment_timestamp)
        self.assertEqual(payment.payment_type, "credit_card")


class TestImportReviewsIntegration(TestCase):
    """Test de la rupture empty title/message."""

    def setUp(self):
        user = User.objects.create_user(
            username="r@r.com", email="r@r.com",
            password="x", role=User.ROLE_CUSTOMER,
        )
        self.customer = Customer.objects.create(user=user)
        from django.utils import timezone as tz
        self.order = Order.objects.create(
            order_id                 = uuid.UUID("73fc7af87114b39712e6da79b0a377eb"),
            customer                 = self.customer,
            order_status             = "delivered",
            order_purchase_timestamp = tz.now(),
        )

    def _run(self, csv_content: str) -> ImportStats:
        import tempfile, os
        cmd = Command(); cmd.batch = 500; cmd.dry = False
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content); tmp = f.name
        try:
            return cmd.import_reviews(tmp)
        finally:
            os.unlink(tmp)

    def test_empty_title_and_message_accepted(self):
        """87k reviews sans titre : doit s'importer sans erreur."""
        csv = 'review_id,order_id,review_score,review_comment_title,review_comment_message,review_creation_date,review_answer_timestamp\n7bc2406110b926393aa56f80a40eba40,73fc7af87114b39712e6da79b0a377eb,4,,,2018-01-18 00:00:00,2018-01-18 21:46:59\n'
        self._run(csv)
        review = Review.objects.first()
        self.assertIsNotNone(review)
        self.assertEqual(review.review_comment_title,   "")
        self.assertEqual(review.review_comment_message, "")


# ─────────────────────────────────────────────────────────────────────────────
# TESTS SPÉCIFIQUES RÉSOLUTION CATÉGORIE (3 niveaux)
# ─────────────────────────────────────────────────────────────────────────────

class TestCategoryResolutionInProduct(TestCase):
    """
    Les 3 niveaux de résolution de catégorie dans _build_product :
      1. Lookup exact → catégorie connue
      2. Absent de la translation → get_or_create à la volée
      3. Nom vide → fallback UNCATEGORIZED_SLUG
    """

    def _row(self, cat_name="perfumaria", **kwargs):
        defaults = dict(
            product_id                 = "1e9e8ef04dbcff4541ed26657ea517e5",
            product_category_name      = cat_name,
            product_name_lenght        = "40",
            product_description_lenght = "287",
            product_photos_qty         = "1",
            product_weight_g           = "225",
            product_length_cm          = "16",
            product_height_cm          = "10",
            product_width_cm           = "14",
        )
        defaults.update(kwargs)
        return MagicMock(**defaults)

    def test_niveau1_lookup_exact(self):
        """Cas standard : catégorie trouvée dans le dict."""
        cat   = MagicMock()
        stats = ImportStats(entity="Product", total=1)
        result = Command._build_product(self._row("perfumaria"), {"perfumaria": cat}, stats)
        self.assertIsNotNone(result)
        self.assertEqual(result.category, cat)
        self.assertEqual(stats.failed, 0)

    def test_niveau3_nom_vide_utilise_fallback(self):
        """
        610 produits ont product_category_name vide.
        → doit utiliser la catégorie UNCATEGORIZED_SLUG si présente dans le dict.
        """
        from app.management.commands.load_olist_data import UNCATEGORIZED_SLUG
        fallback = MagicMock()
        cats     = {UNCATEGORIZED_SLUG: fallback}
        stats    = ImportStats(entity="Product", total=1)
        result   = Command._build_product(self._row(""), cats, stats)
        self.assertIsNotNone(result)
        self.assertEqual(result.category, fallback)
        self.assertEqual(stats.failed, 0)

    def test_niveau3_sans_fallback_enregistre_erreur(self):
        """
        Nom vide ET fallback absente du dict (ex: dry-run sans DB) → erreur.
        """
        stats  = ImportStats(entity="Product", total=1)
        result = Command._build_product(self._row(""), {}, stats)
        self.assertIsNone(result)
        self.assertEqual(stats.failed, 1)


class TestCategoryResolutionIntegration(TestCase):
    """
    Test d'intégration : import_categories crée la fallback,
    import_products résout les 3 cas avec la DB réelle.
    """

    def _run_categories(self, csv_content: str) -> ImportStats:
        import tempfile, os
        cmd = Command(); cmd.batch = 500; cmd.dry = False
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content); tmp = f.name
        try:
            return cmd.import_categories(tmp)
        finally:
            os.unlink(tmp)

    def _run_products(self, csv_content: str) -> ImportStats:
        import tempfile, os
        cmd = Command(); cmd.batch = 500; cmd.dry = False
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content); tmp = f.name
        try:
            return cmd.import_products(tmp)
        finally:
            os.unlink(tmp)

    def test_fallback_category_created_after_import_categories(self):
        """import_categories doit toujours créer la catégorie fallback."""
        from app.management.commands.load_olist_data import UNCATEGORIZED_SLUG
        csv = "product_category_name,product_category_name_english\nperfumaria,health_beauty\n"
        self._run_categories(csv)
        self.assertTrue(Category.objects.filter(
            product_category_name=UNCATEGORIZED_SLUG
        ).exists())

    def test_niveau2_categorie_absente_translation_creee_a_la_volee(self):
        """
        'pc_gamer' et 'portateis_cozinha…' ne sont pas dans la translation.
        → import_products doit les créer automatiquement.
        """
        # Setup : catégories de base + fallback
        csv_cats = "product_category_name,product_category_name_english\nperfumaria,health_beauty\n"
        self._run_categories(csv_cats)

        csv_prods = (
            "product_id,product_category_name,product_name_lenght,product_description_lenght,"
            "product_photos_qty,product_weight_g,product_length_cm,product_height_cm,product_width_cm\n"
            "1e9e8ef04dbcff4541ed26657ea517e5,pc_gamer,40,287,1,225,16,10,14\n"
        )
        stats = self._run_products(csv_prods)

        # Produit importé
        self.assertEqual(Product.objects.count(), 1)
        # Catégorie créée à la volée
        self.assertTrue(Category.objects.filter(product_category_name="pc_gamer").exists())
        # Pas d'erreur
        self.assertEqual(stats.failed, 0)
        # Produit lié à la bonne catégorie
        product = Product.objects.first()
        self.assertEqual(product.category.product_category_name, "pc_gamer")

    def test_niveau3_produit_sans_categorie_lie_a_fallback(self):
        """
        610 produits ont product_category_name vide.
        → tous doivent être liés à la catégorie fallback, aucun rejeté.
        """
        from app.management.commands.load_olist_data import UNCATEGORIZED_SLUG
        csv_cats = "product_category_name,product_category_name_english\nperfumaria,health_beauty\n"
        self._run_categories(csv_cats)

        csv_prods = (
            "product_id,product_category_name,product_name_lenght,product_description_lenght,"
            "product_photos_qty,product_weight_g,product_length_cm,product_height_cm,product_width_cm\n"
            "1e9e8ef04dbcff4541ed26657ea517e5,,40,287,1,225,16,10,14\n"  # catégorie vide
        )
        stats = self._run_products(csv_prods)

        self.assertEqual(Product.objects.count(), 1)
        self.assertEqual(stats.failed, 0)
        product = Product.objects.first()
        self.assertEqual(product.category.product_category_name, UNCATEGORIZED_SLUG)

    def test_all_three_levels_in_one_import(self):
        """
        Un seul import avec les 3 cas simultanément :
        - catégorie connue
        - catégorie absente de translation
        - catégorie vide
        Tous les produits doivent être importés, 0 failed.
        """
        from app.management.commands.load_olist_data import UNCATEGORIZED_SLUG
        csv_cats = "product_category_name,product_category_name_english\nperfumaria,health_beauty\n"
        self._run_categories(csv_cats)

        csv_prods = (
            "product_id,product_category_name,product_name_lenght,product_description_lenght,"
            "product_photos_qty,product_weight_g,product_length_cm,product_height_cm,product_width_cm\n"
            "1e9e8ef04dbcff4541ed26657ea517e5,perfumaria,40,287,1,225,16,10,14\n"  # niveau 1
            "2e9e8ef04dbcff4541ed26657ea517e5,pc_gamer,40,287,1,300,16,10,14\n"    # niveau 2
            "3e9e8ef04dbcff4541ed26657ea517e5,,40,287,1,400,16,10,14\n"            # niveau 3
        )
        stats = self._run_products(csv_prods)

        self.assertEqual(Product.objects.count(), 3)
        self.assertEqual(stats.failed, 0)

        cats_used = set(Product.objects.values_list(
            "category__product_category_name", flat=True
        ))
        self.assertIn("perfumaria",      cats_used)
        self.assertIn("pc_gamer",        cats_used)
        self.assertIn(UNCATEGORIZED_SLUG, cats_used)
