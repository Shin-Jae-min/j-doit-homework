
from homework_manager import HomeworkManager
import logging

logging.basicConfig(level=logging.INFO)

def test():
    manager = HomeworkManager()
    print("Fetching Day 1...")
    hw = manager.get_homework(1)
    print(f"Day 1 Result ({len(hw)} items):")
    for item in hw:
        print(item)
        
    print("\nFetching Day 2...")
    hw2 = manager.get_homework(2)
    print(f"Day 2 Result ({len(hw2)} items):")
    for item in hw2:
        print(item)

if __name__ == "__main__":
    test()
