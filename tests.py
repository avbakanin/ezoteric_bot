"""
Тесты для нумерологического бота
"""

import unittest
import asyncio
from datetime import datetime
from calculations import (
    calculate_life_path_number,
    calculate_soul_number,
    calculate_daily_number,
    validate_date
)
from security import SecurityValidator
from storage import UserStorage

class TestCalculations(unittest.TestCase):
    """Тесты для расчетов"""
    
    def test_life_path_number(self):
        """Тест расчета числа жизненного пути"""
        self.assertEqual(calculate_life_path_number("15.05.1990"), 3)
        self.assertEqual(calculate_life_path_number("01.01.2000"), 4)  # Исправлено: 1+1+2+0+0+0 = 4
        self.assertEqual(calculate_life_path_number("31.12.1999"), 8)
    
    def test_soul_number(self):
        """Тест расчета числа души"""
        self.assertEqual(calculate_soul_number("15.05.1990"), 6)
        self.assertEqual(calculate_soul_number("01.01.2000"), 1)
    
    def test_daily_number(self):
        """Тест расчета числа дня"""
        # Тестируем с текущей датой
        daily = calculate_daily_number()
        self.assertGreaterEqual(daily, 1)
        self.assertLessEqual(daily, 9)
    
    def test_validate_date(self):
        """Тест валидации даты"""
        self.assertTrue(validate_date("15.05.1990"))
        self.assertTrue(validate_date("01.01.2000"))
        self.assertFalse(validate_date("32.05.1990"))
        self.assertFalse(validate_date("15.13.1990"))
        self.assertFalse(validate_date("15.05.1800"))
        self.assertFalse(validate_date("invalid"))

class TestSecurity(unittest.TestCase):
    """Тесты для безопасности"""
    
    def setUp(self):
        self.validator = SecurityValidator()
    
    def test_validate_user_input(self):
        """Тест валидации пользовательского ввода"""
        self.assertTrue(self.validator.validate_user_input("Нормальный текст"))
        self.assertFalse(self.validator.validate_user_input(""))
        self.assertFalse(self.validator.validate_user_input(None))
        self.assertFalse(self.validator.validate_user_input("<script>alert('xss')</script>"))
        self.assertFalse(self.validator.validate_user_input("javascript:alert('xss')"))
    
    def test_sanitize_text(self):
        """Тест очистки текста"""
        self.assertEqual(self.validator.sanitize_text("Нормальный текст"), "Нормальный текст")
        self.assertEqual(self.validator.sanitize_text("<script>alert('xss')</script>"), "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;")
        self.assertEqual(self.validator.sanitize_text(""), "")
    
    def test_validate_date_format(self):
        """Тест валидации формата даты"""
        self.assertTrue(self.validator.validate_date_format("15.05.1990"))
        self.assertTrue(self.validator.validate_date_format("01.01.2000"))
        self.assertFalse(self.validator.validate_date_format("32.05.1990"))
        self.assertFalse(self.validator.validate_date_format("15.13.1990"))
        self.assertFalse(self.validator.validate_date_format("15.05.1800"))
        self.assertFalse(self.validator.validate_date_format("invalid"))
        self.assertFalse(self.validator.validate_date_format(""))

class TestStorage(unittest.TestCase):
    """Тесты для хранилища"""
    
    def setUp(self):
        self.storage = UserStorage()
        self.test_user_id = 12345
    
    def test_user_creation(self):
        """Тест создания пользователя"""
        user = self.storage.get_user(self.test_user_id)
        self.assertIsNotNone(user)
        self.assertIn("created_at", user)
        self.assertIn("last_activity", user)
    
    def test_user_update(self):
        """Тест обновления пользователя"""
        self.storage.update_user(self.test_user_id, name="Test User")
        user = self.storage.get_user(self.test_user_id)
        self.assertEqual(user["name"], "Test User")
    
    def test_text_history(self):
        """Тест истории текстов"""
        # Очищаем историю перед тестом
        self.storage.update_user(self.test_user_id, text_history=[])
        
        self.storage.add_text_to_history(self.test_user_id, "Test text 1")
        self.storage.add_text_to_history(self.test_user_id, "Test text 2")
        
        history = self.storage.get_text_history(self.test_user_id)
        self.assertEqual(len(history), 2)
        self.assertIn("Test text 1", history)
        self.assertIn("Test text 2", history)

def run_tests():
    """Запуск всех тестов"""
    unittest.main(verbosity=2)

if __name__ == "__main__":
    run_tests()
