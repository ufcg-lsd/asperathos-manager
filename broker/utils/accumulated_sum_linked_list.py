from broker.utils.linkedlist import LinkedList, Node


class AccumulatedSumLinkedList(LinkedList):

    def insert(self, element):
        if self.head is None:
            self.push(element)

        elif self.head.value.remaining_time > element.remaining_time:
            node = Node(value=element)
            self.head.value.remaining_time -= element.remaining_time
            node.next = self.head
            self.head = node
        else:
            value = element
            current = self.head
            node = Node(value=element)
            while True:
                value.remaining_time -= current.value.remaining_time
                if value.remaining_time == 0:
                    if current is not None:
                        current.value.app_ids.append(element.app_ids[0])
                        break
                if current.next is None:
                    self.push(value)
                    break
                elif current.next.value.remaining_time > value.remaining_time:
                    node.value.remaining_time = value.remaining_time
                    node.next = current.next
                    node.next.value.remaining_time -= value.remaining_time
                    current.next = node
                    break
                else:
                    current = current.next
