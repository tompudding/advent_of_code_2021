import sys


class Packet:
    name = "base"

    def __init__(self, version, type_id, stream):
        self.version = version
        self.type_id = type_id
        self.length = 6
        self.packets = []

    def print_lines(self):
        yield f"[PACKET:{self.name}] version={self.version} type_id={self.type_id}"

    def __repr__(self):
        return "\n".join(self.print_lines())

    def version_sum(self):
        total = self.version

        for packet in self.packets:
            total += packet.version_sum()

        return total


class LiteralPacket(Packet):
    type_id = 4
    name = "Literal"

    def __init__(self, version, type_id, stream):
        super().__init__(version, type_id, stream)
        self.value = 0
        more = 1
        pos = 0
        while more:
            val = int(stream[pos : pos + 5], 2)
            pos += 5
            more = val >> 4
            self.value <<= 4
            self.value |= val & 0xF
        self.length += pos

    def print_lines(self):
        for line in super().print_lines():
            yield line + f": value={self.value}"


class Operator(Packet):
    type_id = 0
    name = "Unknown Operator"

    def __init__(self, version, type_id, stream):
        super().__init__(version, type_id, stream)
        self.packets = []

        self.operator_type = int(stream[0], 2)
        if self.operator_type:
            self.length += 11 + 1
            self.num_packets = int(stream[1:12], 2)
            self.parse_packets(stream[12:])
        else:
            self.length += 15 + 1
            self.sub_length = int(stream[1:16], 2)
            self.parse_bits(stream[16:])

    def parse_packets(self, stream):
        while len(self.packets) < self.num_packets:
            packet, stream = packet_factory(stream)
            # print(packet, packet.length)
            self.packets.append(packet)
            self.length += packet.length

    def parse_bits(self, stream):
        consumed = 0
        while consumed < self.sub_length:
            # print(f"{consumed=} {self.length=}")
            packet, stream = packet_factory(stream)
            # print(packet)
            self.packets.append(packet)
            consumed += packet.length
            self.length += packet.length
        # print(f"{consumed=} {self.length=}")

    def print_lines(self):
        for line in super().print_lines():
            yield line
            for packet in self.packets:
                for line in packet.print_lines():
                    yield "  " + line


packet_classes = [LiteralPacket]
packet_machines = {packet.type_id: packet for packet in packet_classes}


def packet_factory(stream):
    # print(f"packet factory {stream=}")
    if len(stream) <= 6 or "1" not in stream:
        # we're done
        return None, ""

    version, type_id = int(stream[:3], 2), int(stream[3:6], 2)
    # print("AA", version, type_id)
    try:
        packet_type = packet_machines[type_id]
    except KeyError:
        # print(f"Unknown type_id {type_id}, using operator")
        packet_type = Operator
    packet = packet_type(version, type_id, stream[6:])

    return packet, stream[packet.length :]


# Start by grabbing the hex and binarifying it

with open(sys.argv[1], "r") as file:
    hexa = int(file.read().strip(), 16)
    # it needs prepadding so that it's a multiple of four long
    stream = f"{hexa:b}"
    padding = ((len(stream) + 3) & ~3) - len(stream)
    stream = ("0" * padding) + stream
    print(stream)


total = 0
while len(stream) >= 6 or "1" in stream:
    packet, stream = packet_factory(stream)
    if packet is None:
        break
    print(packet)
    total += packet.version_sum()

print(total)
