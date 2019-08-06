# Author: Javan Lacerda - UFCG - LSD - 2019


class LinkedList():

    def __init__(self):
        self.tail = None
        self.head = None

    def is_empty(self):
        return self.head is None

    def size(self):
        return self.size_aux(self.head)

    def size_aux(self, current):
        if current is not None:
            return 1 + self.size_aux(current.next)
        else:
            return 0

    def search(self, element):
        current = self.head
        while True:
            if current is None:
                return None
            elif current.value == element:
                return element
            current = current.next

    def push(self, element):
        node = Node(value=element)
        if self.is_empty():
            self.head = node
            self.tail = node

        else:
            self.tail.next = node
            self.tail = node

    def pop(self):
        if self.head is not None:
            temp = self.head
            self.head = self.head.next
            return temp

    def remove(self, element):
        if not self.is_empty() and self.head.value == element:
            self.head = self.head.next
        else:
            pntm = self._find_penultimate()
            if pntm is not None and pntm.next.value == element:
                pntm.next = None
                self.tail = pntm
            else:
                fnd = self._find_next_element(element, self.head)
                if fnd is not None:
                    fnd.next = fnd.next.next

    def _find_next_element(self, element, from_node):
        frm = from_node
        while True:
            if frm.next is None:
                return None
            elif frm.next.value == element:
                return frm
            frm = frm.next

    def _find_penultimate(self):
        current = self.head
        if self.is_empty() or self.size() == 1:
            return None

        while current is not None:
            if current.next.next is None:
                return current
            current = current.next

    def to_list(self):
        out_l = []
        current = self.head
        while current is not None:
            out_l.append(current.value)
            current = current.next
        return out_l


class Node():
    def __init__(self, value=None, next=None):
        self.value = value
        self.next = next

    def __str__(self):
        return str(self.value)
