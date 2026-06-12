from deal_sniper.listing import Listing


def test_field_access():
    listing = Listing(title="Red Bike", price=99.99, url="https://ex.com/1", source="test")
    assert listing.title == "Red Bike"
    assert listing.price == 99.99
    assert listing.url == "https://ex.com/1"
    assert listing.source == "test"


def test_extra_defaults_to_empty_dict():
    listing = Listing(title="X", price=1.0, url="u", source="s")
    assert listing.extra == {}


def test_extra_is_independent_per_instance():
    a = Listing(title="A", price=1.0, url="u1", source="s")
    b = Listing(title="B", price=2.0, url="u2", source="s")
    a.extra["key"] = "val"
    assert "key" not in b.extra


def test_extra_can_hold_arbitrary_data():
    listing = Listing(title="X", price=1.0, url="u", source="s", extra={"img": "http://img", "views": 42})
    assert listing.extra["img"] == "http://img"
    assert listing.extra["views"] == 42


def test_price_is_float():
    listing = Listing(title="X", price=5.0, url="u", source="s")
    assert isinstance(listing.price, float)


def test_price_zero():
    listing = Listing(title="Free", price=0.0, url="u", source="s")
    assert listing.price == 0.0


def test_price_negative_stored_as_given():
    # The dataclass doesn't enforce non-negative; store what's given
    listing = Listing(title="X", price=-10.0, url="u", source="s")
    assert listing.price == -10.0


def test_empty_title():
    listing = Listing(title="", price=1.0, url="u", source="s")
    assert listing.title == ""


def test_equality_by_value():
    a = Listing(title="T", price=10.0, url="u", source="s")
    b = Listing(title="T", price=10.0, url="u", source="s")
    assert a == b


def test_different_instances_not_equal():
    a = Listing(title="A", price=1.0, url="u", source="s")
    b = Listing(title="B", price=2.0, url="u2", source="s")
    assert a != b
