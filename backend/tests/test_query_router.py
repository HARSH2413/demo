import pytest
from app.services.query_router import RuleBasedQueryRouter

def test_query_router_empty_history():
    router = RuleBasedQueryRouter()
    decision = router.route("what is it?", 0)
    assert decision["route"] == "normal"

def test_query_router_long_query_no_pronouns():
    router = RuleBasedQueryRouter()
    long_query = "Please provide the total revenue for the company across all regions during the third quarter of the fiscal year."
    decision = router.route(long_query, 2)
    assert decision["route"] == "normal"

def test_query_router_pronouns():
    router = RuleBasedQueryRouter()
    decision = router.route("what did he say about it?", 2)
    assert decision["route"] == "follow_up"

def test_query_router_short():
    router = RuleBasedQueryRouter()
    decision = router.route("revenue numbers", 2)
    assert decision["route"] == "follow_up"
