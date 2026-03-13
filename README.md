hw-test (Python)
— Автоопределение установленного релиза ALT/Альт СП.
— Конфигурирование репозиториев (internet/usb/lan) и обновление.
— Пакетный режим (--batch).
— Базовые автотесты (ping).

Примеры:
1) Показать детект:
   hw-test detect

2) Настроить репозитории по текущей системе (интернет):
   sudo hw-test repo --source internet

3) Обновить систему:
   sudo hw-test upgrade

4) Запустить базовый тест:
   hw-test test --suite basic

5) Пакетный режим (автоопределение релиза, апдейт, тесты):
   hw-test batch '{ "repo_source":"internet", "auto_upgrade_on_boot": true, "tests": ["basic"] }'

Внимание:
— Замените URL в hw_test/repo/sources.py на ваши зеркала ALT (HTTP/LAN/USB).
— Для операций с пакетами требуются root-права.
