def add(x, y):
    return x + y

name = "Kate"
print(add(5, 10))
print(add("abc", "lol"))

if name == 'Alice':
    print('hello, Alice')


class Vehicle(object):

    def __init__(self, color, doors, tries):
        self.color = color
        self.doors = doors
        self.tires = tries

    def brake(self):
        return 'Braking'

    def drive(self):
        return "I'm driving!"