from pymongo import MongoClient

URI = 'mongodb://localhost:27017/'

client = MongoClient(URI)

db = client.todo_db

task_collections = db.tasks

def create_task(description):
    task = {
        'task':description
    }

    result = task_collections.insert_one(task)
    print(f"Task created with id: {result.inserted_id}")

def read_task():
    task = task_collections.find()
    for docs in task:
        print(f"{docs['task']}")

while True:
    print("\n1. Create Task")
    print("2. View Task")
    print("3. Exit")

    choice = int(input("\nEnter Your Choice: "))

    if choice == 1:
        description = input("Enter Your task: ")
        create_task(description)
    elif choice == 2:
        read_task()
    elif choice == 3:
        break
    else:
        print("\nProvide a valid option")
