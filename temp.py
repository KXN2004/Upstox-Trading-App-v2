
class Users:
    def __init__(self, name, age):
        self.name = name
        self.age = age

    def __repr__(self) -> str:
        return f"User({self.name}, {self.age})"

    def __str__(self) -> str:
        return f"{self.name} is {self.age} years old"

    def __add__(self, other):
        return self.age + other.age

    def __mul__(self, other):
        return self.age * other.age

    def __len__(self):
        return len(self.name)

    def __call__(self, x):
        return x + self.age

    def __getitem__(self, i):
        return self.name[i]

    def __setattr__(self, name, value):
        print("Setting attribute...")
        super().__setattr__(name, value)

    def __getattr__(self, name):
        print("Getting attribute...")
        return super().__getattr__(name)

    def __delattr__(self, name):
        print("Deleting attribute...")
        super().__delattr__(name)

    def __iter__(self):
        return iter(self.name)

    def __contains__(self, x):
        return x in self.name

    def __enter__(self):
        print("Entering context...")
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        print("Exiting context...")
        return False

    def __getstate__(self):
        return self.name, self.age

    def __setstate__(self, state):
        self.name, self.age = state

class Student:
    """Student class"""

    def __init__(self) -> None:
        """Constructor"""
        self.name = None
        self.age = None


def main() -> None:
    """Entry point of the program."""

    students = list()

    kevin = Student()
    kevin.name = "John"
    kevin.age = 20

    students.append(kevin)

    vishal = kevin
    vishal.age = 21

    students.append(vishal)

    exit()
    

if __name__ == '__main__':
    main()
