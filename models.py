import json
from dataclasses import asdict, dataclass


@dataclass
class Bus:
    busId: str  # noqa: N815
    lat: float
    lng: float
    route: str


@dataclass
class WindowBounds:
    msg_type = 'newBounds'

    west_lng: float = 0
    east_lng: float = 0
    south_lat: float = 0
    north_lat: float = 0

    def update(self, new):
        for key, value in new.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def is_inside(self, bus):
        # have not yet received data from the browser
        if not any(asdict(self).values()):
            return True
        return (
            (self.south_lat < bus.lat < self.north_lat)
            and (self.west_lng < bus.lng < self.east_lng)
        )


class BusEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Bus):
            return asdict(obj)
        return json.JSONEncoder.default(self, obj)
