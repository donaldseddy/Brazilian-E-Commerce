"""
tests/test_load_olist_data.py

Tests unitaires — django.test.TestCase

Leçon apprise : les méthodes _build_* créent de vrais objets Django
(Order, Product, etc.) dont les champs FK valident le type à l'assignation.
MagicMock() est rejeté → toujours utiliser de vraies instances en DB.

Lancer :
    python manage.py test app.tests.test_load_olist_data
"""

from __future__ import annotations

import uuid

from django.test import TestCase
from django.utils import timezone

from app.management.commands.load_olist_data import (
    UNCATEGORIZED_SLUG,
    Command,
    ImportStats,
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
from utils import normalize_uuid, parse_dt, to_int, to_str

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def make_stats(entity: str = "Test") -> ImportStats:
    return ImportStats(entity=entity, total=1)


def make_customer(email="c@test.com") -> Customer:
    user = User.objects.create_user(
        username=email, email=email, password="x", role=User.ROLE_CUSTOMER
    )
    return Customer.objects.create(user=user)


def make_category(name="test_cat") -> Category:
    return Category.objects.create(
        product_category_name=name,
        product_category_name_english=name.replace("_", " ").title(),
    )


def make_order(customer: Customer, order_id_hex: str | None = None) -> Order:
    oid = normalize_uuid(order_id_hex) if order_id_hex else uuid.uuid4()
    return Order.objects.create(
        order_id=oid,
        customer=customer,
        order_status="delivered",
        order_purchase_timestamp=timezone.now(),
    )


def make_product(category: Category, product_id_hex: str | None = None) -> Product:
    pid = normalize_uuid(product_id_hex) if product_id_hex else uuid.uuid4()
    return Product.objects.create(
        product_id=pid,
        category=category,
        product_name="Test Product",
        product_weight_g=100,
        product_height_cm=10,
        product_description=0,
        product_photo=1,
        product_width_cm=5,
    )


def make_seller(email="s@test.com", seller_id_hex: str | None = None) -> Seller:
    sid = normalize_uuid(seller_id_hex) if seller_id_hex else uuid.uuid4()
    user = User.objects.create_user(
        username=email, email=email, password="x", role=User.ROLE_SELLER
    )
    return Seller.objects.create(seller_id=sid, user=user)


# ─────────────────────────────────────────────────────────────────────────────
# UTILITAIRES PURS
# ─────────────────────────────────────────────────────────────────────────────

class TestNormalizeUuid(TestCase):

    def test_valid_hex_32(self):
        result = normalize_uuid("06b8999e2fba1a1fbc88172c00ba8bc7")
        self.assertIsInstance(result, uuid.UUID)
        self.assertEqual(str(result), "06b8999e-2fba-1a1f-bc88-172c00ba8bc7")

    def test_valid_with_dashes(self):
        self.assertIsInstance(
            normalize_uuid("06b8999e-2fba-1a1f-bc88-172c00ba8bc7"), uuid.UUID
        )

    def test_none_returns_none(self):
        self.assertIsNone(normalize_uuid(None))

    def test_empty_string_returns_none(self):
        self.assertIsNone(normalize_uuid(""))

    def test_invalid_string_returns_none(self):
        self.assertIsNone(normalize_uuid("not-a-uuid"))

    def test_roundtrip(self):
        uid = uuid.uuid4()
        self.assertEqual(normalize_uuid(str(uid)), uid)


class TestToStr(TestCase):

    def test_strips_whitespace(self):
        self.assertEqual(to_str("  hello  "), "hello")

    def test_none_returns_empty(self):
        self.assertEqual(to_str(None), "")

    def test_none_with_default(self):
        self.assertEqual(to_str(None, "fallback"), "fallback")

    def test_nan_returns_empty(self):
        self.assertEqual(to_str("nan"), "")
        self.assertEqual(to_str("NaN"), "")

    def test_numeric(self):
        self.assertEqual(to_str(42), "42")


class TestToInt(TestCase):

    def test_integer_string(self):
        self.assertEqual(to_int("5"), 5)

    def test_float_string_truncated(self):
        self.assertEqual(to_int("3.7"), 3)

    def test_none_returns_none(self):
        self.assertIsNone(to_int(None))

    def test_empty_returns_none(self):
        self.assertIsNone(to_int(""))

    def test_invalid_returns_none(self):
        self.assertIsNone(to_int("abc"))


class TestParseDt(TestCase):

    def test_valid_datetime(self):
        result = parse_dt("2017-10-02 10:56:33")
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.tzinfo)

    def test_none_returns_none(self):
        self.assertIsNone(parse_dt(None))

    def test_empty_returns_none(self):
        self.assertIsNone(parse_dt(""))

    def test_invalid_returns_none(self):
        self.assertIsNone(parse_dt("not-a-date"))


class TestImportStats(TestCase):

    def test_initial_state(self):
        stats = ImportStats(entity="Test", total=100)
        self.assertEqual(stats.imported, 0)
        self.assertEqual(stats.failed, 0)
        self.assertEqual(stats.errors, [])

    def test_record_error_increments_failed(self):
        stats = make_stats()
        stats.record_error("something went wrong")
        self.assertEqual(stats.failed, 1)
        self.assertIn("something went wrong", stats.errors)

    def test_summary_format(self):
        stats = ImportStats(entity="Product", total=100, imported=95, skipped=3, failed=2)
        s = stats.summary()
        self.assertIn("Product", s)
        self.assertIn("95", s)
        self.assertIn("2", s)


# ─────────────────────────────────────────────────────────────────────────────
# _BUILD_* — logique métier
# IMPORTANT : les FK Django rejettent MagicMock → toutes les dépendances
# (Category, Customer, Order, Product, Seller) sont de vraies instances en DB.
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildGeolocation(TestCase):

    def _row(self, **kw):
        from unittest.mock import MagicMock
        d = dict(geolocation_zip_code_prefix="14409", geolocation_lat="-20.5",
                 geolocation_lng="-47.4", geolocation_city="franca", geolocation_state="SP")
        d.update(kw)
        return MagicMock(**d)

    def test_valid_row(self):
        result = Command._build_geolocation(self._row(), make_stats())
        self.assertIsNotNone(result)
        self.assertIsInstance(result, Geolocation)
        self.assertEqual(result.geolocation_zip_code_prefix, "14409")

    def test_zip_padded(self):
        result = Command._build_geolocation(self._row(geolocation_zip_code_prefix="123"), make_stats())
        self.assertEqual(result.geolocation_zip_code_prefix, "00123")

    def test_invalid_lat(self):
        stats  = make_stats()
        result = Command._build_geolocation(self._row(geolocation_lat="not_a_float"), stats)
        self.assertIsNone(result)
        self.assertEqual(stats.failed, 1)


class TestBuildCategory(TestCase):

    def _row(self, name="perfumaria", english="health_beauty"):
        from unittest.mock import MagicMock
        return MagicMock(product_category_name=name, product_category_name_english=english)

    def test_valid_row(self):
        result = Command._build_category(self._row(), make_stats())
        self.assertIsNotNone(result)
        self.assertEqual(result.product_category_name, "perfumaria")

    def test_empty_name_records_error(self):
        stats  = make_stats()
        result = Command._build_category(self._row(name=""), stats)
        self.assertIsNone(result)
        self.assertEqual(stats.failed, 1)


class TestBuildProduct(TestCase):
    """
    Product.category est une FK Django → on a besoin d'une vraie Category en DB.
    MagicMock() est rejeté avec "must be a Category instance".
    """

    def setUp(self):
        self.cat      = make_category("perfumaria")
        self.fallback = Category.objects.create(
            product_category_name=UNCATEGORIZED_SLUG,
            product_category_name_english="Uncategorized",
        )
        self.cats = {
            "perfumaria":     self.cat,
            UNCATEGORIZED_SLUG: self.fallback,
        }

    def _row(self, **kw):
        from unittest.mock import MagicMock
        d = dict(
            product_id="1e9e8ef04dbcff4541ed26657ea517e5",
            product_category_name="perfumaria",
            product_name="Creme Hidratante",
            product_name_lenght="40",
            product_description_lenght="287",
            product_photos_qty="1",
            product_weight_g="225",
            product_length_cm="16",
            product_height_cm="10",
            product_width_cm="14",
        )
        d.update(kw)
        return MagicMock(**d)

    def test_valid_row(self):
        result = Command._build_product(self._row(), self.cats, make_stats())
        self.assertIsNotNone(result)
        self.assertEqual(result.product_weight_g, 225)

    def test_category_assigned(self):
        result = Command._build_product(self._row(), self.cats, make_stats())
        self.assertEqual(result.category, self.cat)

    def test_invalid_uuid(self):
        stats  = make_stats()
        result = Command._build_product(self._row(product_id="bad"), self.cats, stats)
        self.assertIsNone(result)
        self.assertEqual(stats.failed, 1)

    def test_missing_weight(self):
        stats  = make_stats()
        result = Command._build_product(self._row(product_weight_g=""), self.cats, stats)
        self.assertIsNone(result)
        self.assertEqual(stats.failed, 1)

    def test_missing_height(self):
        stats  = make_stats()
        result = Command._build_product(self._row(product_height_cm=""), self.cats, stats)
        self.assertIsNone(result)
        self.assertEqual(stats.failed, 1)

    def test_empty_category_uses_fallback(self):
        """610 produits sans catégorie → catégorie fallback."""
        result = Command._build_product(
            self._row(product_category_name=""), self.cats, make_stats()
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.category, self.fallback)

    def test_empty_category_no_fallback_records_error(self):
        stats  = make_stats()
        result = Command._build_product(self._row(product_category_name=""), {}, stats)
        self.assertIsNone(result)
        self.assertEqual(stats.failed, 1)


class TestBuildCustomerPair(TestCase):
    """
    _build_customer_pair retourne (User non-sauvegardé, uuid.UUID).
    User n'est pas encore en DB → pas de FK à valider ici.
    """

    def _row(self, **kw):
        from unittest.mock import MagicMock
        d = dict(
            customer_id="06b8999e2fba1a1fbc88172c00ba8bc7",
            customer_zip_code_prefix="14409",
            customer_city="franca", customer_state="SP",
            customer_first_name="Ana", customer_last_name="Silva",
            customer_address="Rua Minas Gerais, 919",
        )
        d.update(kw)
        return MagicMock(**d)

    def test_valid_row_returns_tuple(self):
        result = Command._build_customer_pair(self._row(), {}, make_stats())
        self.assertIsNotNone(result)
        user, cid = result
        self.assertIsInstance(user, User)
        self.assertIsInstance(cid, uuid.UUID)

    def test_user_fields(self):
        user, _ = Command._build_customer_pair(self._row(), {}, make_stats())
        self.assertEqual(user.first_name, "Ana")
        self.assertEqual(user.last_name, "Silva")
        self.assertEqual(user.role, User.ROLE_CUSTOMER)
        self.assertFalse(user.is_active)

    def test_city_title_cased(self):
        user, _ = Command._build_customer_pair(
            self._row(customer_city="sao paulo"), {}, make_stats()
        )
        self.assertEqual(user.city, "Sao Paulo")

    def test_state_uppercased(self):
        user, _ = Command._build_customer_pair(
            self._row(customer_state="sp"), {}, make_stats()
        )
        self.assertEqual(user.state, "SP")

    def test_invalid_uuid_records_error(self):
        stats  = make_stats()
        result = Command._build_customer_pair(self._row(customer_id="bad"), {}, stats)
        self.assertIsNone(result)
        self.assertEqual(stats.failed, 1)


class TestBuildSellerPair(TestCase):

    def _row(self, **kw):
        from unittest.mock import MagicMock
        d = dict(
            seller_id="3442f8959a84dea7ee197c632cb2df15",
            seller_zip_code_prefix="13023",
            seller_city="campinas", seller_state="SP",
            seller_first_name="Renata", seller_last_name="Silva",
            seller_full_address="Av. Atlântica, 8571",
        )
        d.update(kw)
        return MagicMock(**d)

    def test_valid_row_returns_tuple(self):
        result = Command._build_seller_pair(self._row(), {}, make_stats())
        self.assertIsNotNone(result)
        user, sid = result
        self.assertIsInstance(user, User)
        self.assertEqual(user.role, User.ROLE_SELLER)

    def test_invalid_uuid_records_error(self):
        stats  = make_stats()
        result = Command._build_seller_pair(self._row(seller_id="xxx"), {}, stats)
        self.assertIsNone(result)
        self.assertEqual(stats.failed, 1)

    def test_address_field(self):
        user, _ = Command._build_seller_pair(self._row(), {}, make_stats())
        self.assertEqual(user.address, "Av. Atlântica, 8571")


class TestBuildOrder(TestCase):
    """
    Order.customer est une FK → on a besoin d'un vrai Customer en DB.
    """

    # IDs fixes pour correspondre aux rows de test
    CUSTOMER_HEX = "9ef432eb6251297304e76186b10a928d"
    ORDER_HEX    = "e481f51cbdc54678b7cc49136f2d6af7"

    def setUp(self):
        user = User.objects.create_user(
            username="order_test@test.com",
            email="order_test@test.com",
            password="x",
            role=User.ROLE_CUSTOMER,
        )
        self.customer = Customer.objects.create(
            customer_id=normalize_uuid(self.CUSTOMER_HEX),
            user=user,
        )

    def _customers(self):
        return {str(self.customer.customer_id): self.customer}

    def _row(self, **kw):
        from unittest.mock import MagicMock
        d = dict(
            order_id=self.ORDER_HEX,
            customer_id=self.CUSTOMER_HEX,
            order_status="delivered",
            order_purchase_timestamp="2017-10-02 10:56:33",
            order_approved_at="2017-10-02 11:07:15",
            order_delivered_carrier_date="",
            order_delivered_customer_date="",
            order_estimated_delivery_date="2017-10-18 00:00:00",
        )
        d.update(kw)
        return MagicMock(**d)

    def test_valid_row(self):
        result = Command._build_order(self._row(), self._customers(), make_stats())
        self.assertIsNotNone(result)
        self.assertEqual(result.order_status, "delivered")

    def test_customer_assigned(self):
        result = Command._build_order(self._row(), self._customers(), make_stats())
        self.assertEqual(result.customer, self.customer)

    def test_invalid_order_uuid(self):
        stats  = make_stats()
        result = Command._build_order(self._row(order_id="bad"), self._customers(), stats)
        self.assertIsNone(result)
        self.assertEqual(stats.failed, 1)

    def test_unknown_customer_records_error(self):
        stats  = make_stats()
        result = Command._build_order(self._row(), {}, stats)
        self.assertIsNone(result)
        self.assertEqual(stats.failed, 1)

    def test_optional_dates_empty(self):
        result = Command._build_order(self._row(), self._customers(), make_stats())
        self.assertIsNotNone(result)
        self.assertIsNone(result.order_delivered_carrier_date)
        self.assertIsNone(result.order_delivered_customer_date)

    def test_purchase_timestamp_fallback(self):
        """Timestamp vide → fallback timezone.now(), jamais NULL."""
        result = Command._build_order(
            self._row(order_purchase_timestamp=""), self._customers(), make_stats()
        )
        self.assertIsNotNone(result)
        self.assertIsNotNone(result.order_purchase_timestamp)


class TestBuildOrderItem(TestCase):
    """
    OrderItem.order / product / seller sont des FK → vraies instances requises.
    """

    ORDER_HEX   = "00010242fe8c5a6d1ba2dd792cb16214"
    PRODUCT_HEX = "4244733e06e7ecb4970a6e2683c13e61"
    SELLER_HEX  = "48436dade18ac8b2bce089ec2a041202"

    def setUp(self):
        cat           = make_category("oi_cat")
        customer      = make_customer("oi_c@test.com")
        self.order    = make_order(customer, self.ORDER_HEX)
        self.product  = make_product(cat, self.PRODUCT_HEX)
        self.seller   = make_seller("oi_s@test.com", self.SELLER_HEX)

    def _dicts(self):
        return (
            {str(self.order.order_id):   self.order},
            {str(self.product.product_id): self.product},
            {str(self.seller.seller_id): self.seller},
        )

    def _row(self, **kw):
        from unittest.mock import MagicMock
        d = dict(
            order_id=self.ORDER_HEX,
            order_item_id="1",
            product_id=self.PRODUCT_HEX,
            seller_id=self.SELLER_HEX,
            shipping_limit_date="2017-09-19 09:45:35",
            price="58.90",
            freight_value="13.29",
        )
        d.update(kw)
        return MagicMock(**d)

    def test_valid_row(self):
        orders, prods, sellers = self._dicts()
        result = Command._build_order_item(self._row(), orders, prods, sellers, make_stats())
        self.assertIsNotNone(result)
        self.assertEqual(result.order_item_sequence_number, 1)

    def test_sequence_is_int(self):
        orders, prods, sellers = self._dicts()
        result = Command._build_order_item(self._row(order_item_id="3"), orders, prods, sellers, make_stats())
        self.assertEqual(result.order_item_sequence_number, 3)
        self.assertIsInstance(result.order_item_sequence_number, int)

    def test_missing_order(self):
        _, prods, sellers = self._dicts()
        stats  = make_stats()
        result = Command._build_order_item(self._row(), {}, prods, sellers, stats)
        self.assertIsNone(result)
        self.assertEqual(stats.failed, 1)

    def test_missing_product(self):
        orders, _, sellers = self._dicts()
        stats  = make_stats()
        result = Command._build_order_item(self._row(), orders, {}, sellers, stats)
        self.assertIsNone(result)
        self.assertEqual(stats.failed, 1)

    def test_missing_seller(self):
        orders, prods, _ = self._dicts()
        stats  = make_stats()
        result = Command._build_order_item(self._row(), orders, prods, {}, stats)
        self.assertIsNone(result)
        self.assertEqual(stats.failed, 1)

    def test_invalid_sequence(self):
        orders, prods, sellers = self._dicts()
        stats  = make_stats()
        result = Command._build_order_item(self._row(order_item_id="abc"), orders, prods, sellers, stats)
        self.assertIsNone(result)
        self.assertEqual(stats.failed, 1)


class TestBuildPayment(TestCase):
    """
    Payment.order est une FK → vrai Order en DB requis.
    """

    ORDER_HEX = "b81ef226f3fe1789b1e8b2acac839d17"

    def setUp(self):
        customer   = make_customer("pay@test.com")
        self.order = make_order(customer, self.ORDER_HEX)

    def _orders(self):
        return {str(self.order.order_id): self.order}

    def _row(self, **kw):
        from unittest.mock import MagicMock
        d = dict(
            order_id=self.ORDER_HEX,
            payment_sequential="1",
            payment_type="credit_card",
            payment_installments="8",
            payment_value="99.33",
        )
        d.update(kw)
        return MagicMock(**d)

    def test_valid_row(self):
        result = Command._build_payment(self._row(), self._orders(), make_stats())
        self.assertIsNotNone(result)
        self.assertEqual(result.payment_type, "credit_card")
        self.assertEqual(result.payment_installments, 8)

    def test_payment_timestamp_always_set(self):
        """payment_timestamp absent du CSV → injecté par timezone.now()."""
        result = Command._build_payment(self._row(), self._orders(), make_stats())
        self.assertIsNotNone(result.payment_timestamp)

    def test_payment_value_float(self):
        result = Command._build_payment(self._row(), self._orders(), make_stats())
        self.assertAlmostEqual(float(result.payment_value), 99.33, places=2)

    def test_unknown_order_records_error(self):
        stats  = make_stats()
        result = Command._build_payment(self._row(), {}, stats)
        self.assertIsNone(result)
        self.assertEqual(stats.failed, 1)

    def test_invalid_sequential_records_error(self):
        stats  = make_stats()
        result = Command._build_payment(self._row(payment_sequential=""), self._orders(), stats)
        self.assertIsNone(result)
        self.assertEqual(stats.failed, 1)


class TestBuildReview(TestCase):
    """
    Review.order est une FK → vrai Order en DB requis.
    Rupture : 87 658 reviews ont title/message vides → doivent être "".
    """

    ORDER_HEX  = "73fc7af87114b39712e6da79b0a377eb"
    REVIEW_HEX = "7bc2406110b926393aa56f80a40eba40"

    def setUp(self):
        customer   = make_customer("rev@test.com")
        self.order = make_order(customer, self.ORDER_HEX)

    def _orders(self):
        return {str(self.order.order_id): self.order}

    def _row(self, **kw):
        from unittest.mock import MagicMock
        d = dict(
            review_id=self.REVIEW_HEX,
            order_id=self.ORDER_HEX,
            review_score="4",
            review_comment_title="",
            review_comment_message="",
            review_creation_date="2018-01-18 00:00:00",
            review_answer_timestamp="2018-01-18 21:46:59",
        )
        d.update(kw)
        return MagicMock(**d)

    def test_valid_row(self):
        result = Command._build_review(self._row(), self._orders(), make_stats())
        self.assertIsNotNone(result)
        self.assertEqual(result.review_score, 4)

    def test_empty_title_is_empty_string_not_none(self):
        """Rupture : NaN/vide → "" pour éviter le NOT NULL constraint."""
        result = Command._build_review(self._row(), self._orders(), make_stats())
        self.assertEqual(result.review_comment_title, "")
        self.assertEqual(result.review_comment_message, "")

    def test_nan_title_becomes_empty_string(self):
        result = Command._build_review(
            self._row(review_comment_title="nan"), self._orders(), make_stats()
        )
        self.assertEqual(result.review_comment_title, "")

    def test_populated_title_preserved(self):
        result = Command._build_review(
            self._row(review_comment_title="Excellent produit"), self._orders(), make_stats()
        )
        self.assertEqual(result.review_comment_title, "Excellent produit")

    def test_invalid_uuid_records_error(self):
        stats  = make_stats()
        result = Command._build_review(self._row(review_id="bad"), self._orders(), stats)
        self.assertIsNone(result)
        self.assertEqual(stats.failed, 1)

    def test_unknown_order_records_error(self):
        stats  = make_stats()
        result = Command._build_review(self._row(), {}, stats)
        self.assertIsNone(result)
        self.assertEqual(stats.failed, 1)

    def test_invalid_score_records_error(self):
        stats  = make_stats()
        result = Command._build_review(self._row(review_score=""), self._orders(), stats)
        self.assertIsNone(result)
        self.assertEqual(stats.failed, 1)

    def test_answer_timestamp_optional(self):
        """review_answer_timestamp vide → None, sans erreur."""
        result = Command._build_review(
            self._row(review_answer_timestamp=""), self._orders(), make_stats()
        )
        self.assertIsNotNone(result)
        self.assertIsNone(result.review_answer_timestamp)


# ─────────────────────────────────────────────────────────────────────────────
# INTÉGRATION — import_* avec vrais CSV et vraie DB
# ─────────────────────────────────────────────────────────────────────────────

def _write_csv(content: str) -> str:
    """Écrit un CSV temporaire, retourne le chemin."""
    import os
    import tempfile
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
    f.write(content)
    f.close()
    return f.name


def _cmd() -> Command:
    c = Command()
    c.batch = 500
    c.dry = False
    return c


class TestImportGeolocationsIntegration(TestCase):

    def _run(self, csv: str) -> ImportStats:
        import os
        path = _write_csv(csv)
        try:
            return _cmd().import_geolocations(path)
        finally:
            os.unlink(path)

    def test_creates_row(self):
        stats = self._run(
            "geolocation_zip_code_prefix,geolocation_lat,geolocation_lng,geolocation_city,geolocation_state\n"
            "14409,-20.5,-47.4,franca,SP\n"
        )
        self.assertEqual(Geolocation.objects.count(), 1)
        self.assertEqual(stats.imported, 1)

    def test_idempotent(self):
        csv = (
            "geolocation_zip_code_prefix,geolocation_lat,geolocation_lng,geolocation_city,geolocation_state\n"
            "14409,-20.5,-47.4,franca,SP\n"
        )
        self._run(csv)
        self._run(csv)
        self.assertEqual(Geolocation.objects.count(), 1)

    def test_invalid_row_skipped(self):
        stats = self._run(
            "geolocation_zip_code_prefix,geolocation_lat,geolocation_lng,geolocation_city,geolocation_state\n"
            "14409,not_float,-47.4,franca,SP\n"
            "01310,-23.5,-46.6,sao paulo,SP\n"
        )
        self.assertEqual(Geolocation.objects.count(), 1)
        self.assertEqual(stats.failed, 1)


class TestImportCategoriesIntegration(TestCase):

    def test_creates_categories_plus_fallback(self):
        import os
        csv  = "product_category_name,product_category_name_english\nperfumaria,health_beauty\nbrinquedos,toys\n"
        path = _write_csv(csv)
        try:
            stats = _cmd().import_categories(path)
        finally:
            os.unlink(path)
        # 2 du CSV + 1 fallback créée automatiquement
        self.assertEqual(Category.objects.count(), 3)
        self.assertTrue(Category.objects.filter(product_category_name=UNCATEGORIZED_SLUG).exists())
        self.assertEqual(stats.imported, 2)


class TestImportCustomersIntegration(TestCase):

    def setUp(self):
        Geolocation.objects.create(
            geolocation_zip_code_prefix="14409",
            geolocation_lat=-20.5, geolocation_lng=-47.4,
            geolocation_city="franca", geolocation_state="SP",
        )

    def _run(self, csv: str) -> ImportStats:
        import os
        path = _write_csv(csv)
        try:
            return _cmd().import_customers(path)
        finally:
            os.unlink(path)

    def _csv(self, cid="06b8999e2fba1a1fbc88172c00ba8bc7"):
        return (
            "customer_id,customer_unique_id,customer_zip_code_prefix,customer_city,"
            "customer_state,customer_first_name,customer_last_name,customer_address\n"
            f"{cid},{cid},14409,franca,SP,Ana,Silva,Rua Minas Gerais 919\n"
        )

    def test_creates_user_and_customer(self):
        self._run(self._csv())
        self.assertEqual(User.objects.filter(role=User.ROLE_CUSTOMER).count(), 1)
        self.assertEqual(Customer.objects.count(), 1)
        self.assertIsNotNone(Customer.objects.first().user)

    def test_demographic_data_on_user(self):
        """Rupture : first_name/city/state sont sur User, pas sur Customer."""
        self._run(self._csv())
        user = User.objects.get(role=User.ROLE_CUSTOMER)
        self.assertEqual(user.first_name, "Ana")
        self.assertEqual(user.last_name, "Silva")
        self.assertEqual(user.city, "Franca")
        self.assertEqual(user.state, "SP")

    def test_customer_uuid_matches_csv(self):
        self._run(self._csv())
        expected = uuid.UUID("06b8999e2fba1a1fbc88172c00ba8bc7")
        self.assertEqual(Customer.objects.first().customer_id, expected)

    def test_imported_accounts_are_inactive(self):
        self._run(self._csv())
        self.assertFalse(User.objects.get(role=User.ROLE_CUSTOMER).is_active)


class TestImportPaymentsIntegration(TestCase):

    def setUp(self):
        customer   = make_customer("pay_int@test.com")
        self.order = make_order(customer, "b81ef226f3fe1789b1e8b2acac839d17")

    def test_payment_created_with_timestamp(self):
        import os
        csv = (
            "order_id,payment_sequential,payment_type,payment_installments,payment_value\n"
            "b81ef226f3fe1789b1e8b2acac839d17,1,credit_card,8,99.33\n"
        )
        path = _write_csv(csv)
        try:
            _cmd().import_payments(path)
        finally:
            os.unlink(path)
        payment = Payment.objects.first()
        self.assertIsNotNone(payment)
        self.assertIsNotNone(payment.payment_timestamp)
        self.assertEqual(payment.payment_type, "credit_card")


class TestImportReviewsIntegration(TestCase):

    def setUp(self):
        customer   = make_customer("rev_int@test.com")
        self.order = make_order(customer, "73fc7af87114b39712e6da79b0a377eb")

    def test_empty_title_and_message_accepted(self):
        import os
        csv = (
            "review_id,order_id,review_score,review_comment_title,review_comment_message,"
            "review_creation_date,review_answer_timestamp\n"
            "7bc2406110b926393aa56f80a40eba40,73fc7af87114b39712e6da79b0a377eb,4,,,"
            "2018-01-18 00:00:00,2018-01-18 21:46:59\n"
        )
        path = _write_csv(csv)
        try:
            _cmd().import_reviews(path)
        finally:
            os.unlink(path)
        review = Review.objects.first()
        self.assertIsNotNone(review)
        self.assertEqual(review.review_comment_title, "")
        self.assertEqual(review.review_comment_message, "")


# ─────────────────────────────────────────────────────────────────────────────
# RÉSOLUTION CATÉGORIE — 3 niveaux
# ─────────────────────────────────────────────────────────────────────────────

class TestCategoryResolutionUnit(TestCase):

    def setUp(self):
        self.cat      = make_category("perfumaria")
        self.fallback = Category.objects.create(
            product_category_name=UNCATEGORIZED_SLUG,
            product_category_name_english="Uncategorized",
        )

    def _row(self, cat_name="perfumaria"):
        from unittest.mock import MagicMock
        return MagicMock(
            product_id="1e9e8ef04dbcff4541ed26657ea517e5",
            product_category_name=cat_name,
            product_name="Produto Teste",
            product_name_lenght="40",
            product_description_lenght="287",
            product_photos_qty="1",
            product_weight_g="225",
            product_length_cm="16",
            product_height_cm="10",
            product_width_cm="14",
        )

    def test_niveau1_lookup_exact(self):
        cats   = {"perfumaria": self.cat, UNCATEGORIZED_SLUG: self.fallback}
        result = Command._build_product(self._row("perfumaria"), cats, make_stats())
        self.assertIsNotNone(result)
        self.assertEqual(result.category, self.cat)

    def test_niveau2_absent_de_translation_creee_en_db(self):
        """pc_gamer absent du dict → get_or_create déclenché."""
        cats   = {UNCATEGORIZED_SLUG: self.fallback}
        result = Command._build_product(self._row("pc_gamer"), cats, make_stats())
        self.assertIsNotNone(result)
        self.assertTrue(Category.objects.filter(product_category_name="pc_gamer").exists())
        self.assertEqual(result.category.product_category_name, "pc_gamer")

    def test_niveau3_nom_vide_utilise_fallback(self):
        cats   = {UNCATEGORIZED_SLUG: self.fallback}
        result = Command._build_product(self._row(""), cats, make_stats())
        self.assertIsNotNone(result)
        self.assertEqual(result.category, self.fallback)

    def test_niveau3_sans_fallback_records_error(self):
        stats  = make_stats()
        result = Command._build_product(self._row(""), {}, stats)
        self.assertIsNone(result)
        self.assertEqual(stats.failed, 1)


class TestCategoryResolutionIntegration(TestCase):

    PRODUCTS_HEADER = (
        "product_id,product_category_name,product_name,"
        "product_name_lenght,product_description_lenght,"
        "product_photos_qty,product_weight_g,product_length_cm,"
        "product_height_cm,product_width_cm"
    )

    def _run_cats(self, csv: str) -> ImportStats:
        import os
        path = _write_csv(csv)
        try:
            return _cmd().import_categories(path)
        finally:
            os.unlink(path)

    def _run_prods(self, csv: str) -> ImportStats:
        import os
        path = _write_csv(csv)
        try:
            return _cmd().import_products(path)
        finally:
            os.unlink(path)

    def _setup_cats(self):
        self._run_cats(
            "product_category_name,product_category_name_english\n"
            "perfumaria,health_beauty\n"
        )

    def _prod_row(self, pid, cat, name="Produto"):
        return f"{pid},{cat},{name},40,287,1,225,16,10,14"

    def test_fallback_created_by_import_categories(self):
        self._setup_cats()
        self.assertTrue(
            Category.objects.filter(product_category_name=UNCATEGORIZED_SLUG).exists()
        )

    def test_niveau2_categorie_creee_a_la_volee(self):
        self._setup_cats()
        csv = (self.PRODUCTS_HEADER + "\n" +
               self._prod_row("1e9e8ef04dbcff4541ed26657ea517e5", "pc_gamer"))
        stats = self._run_prods(csv)
        self.assertEqual(Product.objects.count(), 1)
        self.assertTrue(Category.objects.filter(product_category_name="pc_gamer").exists())
        self.assertEqual(stats.failed, 0)

    def test_niveau3_produit_sans_categorie_lie_a_fallback(self):
        self._setup_cats()
        csv = (self.PRODUCTS_HEADER + "\n" +
               self._prod_row("1e9e8ef04dbcff4541ed26657ea517e5", ""))
        stats = self._run_prods(csv)
        self.assertEqual(Product.objects.count(), 1)
        self.assertEqual(stats.failed, 0)
        self.assertEqual(
            Product.objects.first().category.product_category_name,
            UNCATEGORIZED_SLUG
        )

    def test_all_three_levels(self):
        """3 niveaux simultanément → 3 produits importés, 0 erreur."""
        self._setup_cats()
        csv = (
            self.PRODUCTS_HEADER + "\n" +
            self._prod_row("1e9e8ef04dbcff4541ed26657ea517e5", "perfumaria") + "\n" +
            self._prod_row("2e9e8ef04dbcff4541ed26657ea517e5", "pc_gamer")   + "\n" +
            self._prod_row("3e9e8ef04dbcff4541ed26657ea517e5", "")
        )
        stats = self._run_prods(csv)
        self.assertEqual(Product.objects.count(), 3)
        self.assertEqual(stats.failed, 0)
        cats_used = set(Product.objects.values_list(
            "category__product_category_name", flat=True
        ))
        self.assertIn("perfumaria",       cats_used)
        self.assertIn("pc_gamer",         cats_used)
        self.assertIn(UNCATEGORIZED_SLUG, cats_used)
