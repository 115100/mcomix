import unittest

from mcomix import tools

class TestAlphanumericSort(unittest.TestCase):
    def test_numbers_are_ordered_naturally(self):
        lst = ['10.jpg', '2.jpg']
        tools.alphanumeric_sort(lst)
        self.assertListEqual(lst, ['2.jpg', '10.jpg'])

    def test_sort_with_mixed_number_and_string_files(self):
        lst = ['text_2.jpg', '2_text.jpg']
        tools.alphanumeric_sort(lst)
        self.assertListEqual(lst, ['2_text.jpg', 'text_2.jpg'])
