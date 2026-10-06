import unittest
from decimal import Decimal as D
from portfolio_price_rules import source_grams, mapping_factor, preference

class PriceRulesTest(unittest.TestCase):
    def test_converted_kg_uses_final_unit(self):
        self.assertEqual(source_grams('20kg(1kg)','111')[0],D(1000))
    def test_livestock_100g_is_not_kg(self):
        self.assertEqual(source_grams('목심(100g)','4304')[0],D(100))
        self.assertEqual(D(2648)*1000/source_grams('목심(100g)','4304')[0],D(26480))
    def test_counts_and_liters(self):
        self.assertEqual(source_grams('애호박(20개)','224')[0],D(7000))
        self.assertEqual(source_grams('특란10구(10구)','9903')[0],D(500))
        self.assertEqual(source_grams('흰우유(1L)','9908')[0],D(1030))
    def test_unknown_units_are_not_guessed(self):
        with self.assertRaises(ValueError):source_grams('알 수 없음','111')
    def test_rice_cooking_and_seaweed_rehydration(self):
        self.assertEqual(mapping_factor('멥쌀, 백미, 밥','20kg(1kg)','111')[0],D('0.4'))
        self.assertEqual(mapping_factor('미역, 생것','마른미역(1kg)','642')[0],D('0.125'))
    def test_roasted_laver_not_cooked_twice(self):
        self.assertEqual(mapping_factor('김, 참김, 구운것','구운김(10장)','641')[0],D(1))
    def test_dried_and_fermented_sources(self):
        self.assertEqual(preference('새우, 젓갈')[0],'650')
        self.assertEqual(preference('오징어, 말린것')[0],'640')
        self.assertEqual(preference('오이, 취청, 생것')[:2],('223','03'))
    def test_shellfish_edible_yield(self):
        self.assertEqual(mapping_factor('바지락, 생것','냉장(1kg)','661')[0],D(4))

if __name__=='__main__':unittest.main()
