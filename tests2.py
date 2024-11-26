import unittest
from unittest.mock import patch, MagicMock
import os
import main


class TestDependencyVisualizer(unittest.TestCase):
    def setUp(self):
        """Инициализация тестового объекта."""
        self.visualizer = main.DependencyVisualizer()
        self.visualizer.packsAndDeps = {
            "packageA": ["packageB", "packageC>=1.0"],
            "packageB": ["packageD"],
            "packageC": [],
            "packageD": [],
        }
        self.visualizer.packsByProvided = {
            "providedB": "packageB"
        }

    def test_start(self):
        """Тест загрузки и парсинга данных из APKINDEX."""
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.content = b''
            mock_get.return_value = mock_response
            with patch('tarfile.open') as mock_tarfile:
                mock_tarfile.return_value = MagicMock()
                self.visualizer.start()
        # Проверяем, что вызов прошел
        mock_get.assert_called_once()
        mock_tarfile.assert_called_once()

    def test_addDepends(self):
        """Тест рекурсивного добавления зависимостей."""
        self.visualizer.result = ""
        self.visualizer.setOfPacks = set()
        self.visualizer.addDepends("packageA")

        expected_result = "packageA --> packageB\npackageA --> packageC\npackageB --> packageD\n"
        self.assertEqual(self.visualizer.result, expected_result)

    def test_get_graph(self):
        """Тест генерации ссылки на граф зависимостей."""
        with patch.object(self.visualizer, 'addDepends') as mock_addDepends:
            mock_addDepends.return_value = None
            self.visualizer.result = "graph\npackageA --> packageB\n"
            link = self.visualizer.get_graph("packageA")
            self.assertIn("https://mermaid.ink/img/", link)

    @patch('requests.get')
    @patch('subprocess.run')
    def test_display_graph(self, mock_run, mock_get):
        """Тест отображения графа: загрузка и вызов Bash-скрипта."""
        mock_response = MagicMock()
        mock_response.content = b'image data'
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        with patch('builtins.open', unittest.mock.mock_open()) as mock_file:
            self.visualizer.display_graph("packageA", "test_script.sh")
            # Проверяем, что изображение скачивается
            mock_get.assert_called_once()
            # Проверяем, что изображение сохраняется
            mock_file.assert_called_once_with("downloaded_image.png", "wb")
            # Проверяем, что Bash-скрипт вызывается
            mock_run.assert_called_once_with(
                ["bash", "test_script.sh", "downloaded_image.png"],
                check=True
            )


if __name__ == "__main__":
    unittest.main()
