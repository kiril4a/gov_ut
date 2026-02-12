import gspread

def clean_drive():
    print("Подключение к Google Drive...")
    try:
        gc = gspread.service_account(filename='service_account.json')
        
        # Получаем список всех таблиц
        files = gc.list_spreadsheet_files()
        print(f"Найдено файлов: {len(files)}")
        
        deleted_count = 0
        for f in files:
            name = f['name']
            file_id = f['id']
            
            # Удаляем все файлы или только дубликаты EmployeeData
            # Снимаем защиту предупреждением
            print(f"Найден файл: {name} ({file_id})")
            
            if name == "EmployeeData":
                print(f"Удаляю старый файл: {name}...")
                try:
                    gc.del_spreadsheet(file_id)
                    deleted_count += 1
                    print("ОК")
                except Exception as e:
                    print(f"Ошибка удаления: {e}")
            else:
                 print("Пропускаю (не EmployeeData)")

        print(f"\nГотово. Удалено файлов: {deleted_count}")
        print("Теперь попробуйте войти в приложение снова. Скрипт создаст одну новую чистую таблицу.")

    except Exception as e:
        print(f"Критическая ошибка: {e}")

if __name__ == "__main__":
    confirm = input("Этот скрипт удалит ВСЕ таблицы с названием 'EmployeeData' на сервисном аккаунте.\nВведите 'yes' для продолжения: ")
    if confirm.lower() == 'yes':
        clean_drive()
    else:
        print("Отмена.")
