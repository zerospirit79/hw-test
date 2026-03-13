pc-test (Python)
— Автоопределение установленного релиза ALT/Альт СП.
— Конфигурирование репозиториев (internet/usb/lan) и обновление.
— Пакетный режим (--batch).
— Базовые автотесты (ping).

Примеры:
1) Показать детект:
   pc-test detect

2) Настроить репозитории по текущей системе (интернет):
   sudo pc-test repo --source internet

3) Обновить систему:
   sudo pc-test upgrade

4) Запустить базовый тест:
   pc-test test --suite basic

5) Пакетный режим (автоопределение релиза, апдейт, тесты):
   pc-test batch '{ "repo_source":"internet", "auto_upgrade_on_boot": true, "tests": ["basic"] }'

Внимание:
— Замените URL в pc_test/repo/sources.py на ваши зеркала ALT (HTTP/LAN/USB).
— Для операций с пакетами требуются root-права.
