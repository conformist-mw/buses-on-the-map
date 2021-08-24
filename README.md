# Buses on the City Map

The application shows the movement of buses on the map in real-time.

![buses](https://user-images.githubusercontent.com/13550539/130320606-9f578e72-63aa-4e33-8574-9b210c91e57a.gif)

### How to run

#### Installation

```shell
pip install -r requirements.txt
```

#### Server

```shell
python server.py
```

Possible options:

```shell
--bus-port  # port for fake_bus.py generator
--browser-port  # port to communicate with browser
--verbose  # to increase logging level
```

#### Fake buses (to generate events)

```shell
python fake_bus.py
```

Possible options:

```shell
--server  # websocket server address
--routes-number  # how many routes will be loaded
--buses-per-route  # generate routes with offset
--websockets-count  # how many websockets will be opened
--emulator-id  # busId prefix if multiple fake_bus instances running
--refresh-timeout  # timeout between sending new coordinates
--verbose  # to increase logging level
```


### Settings

You can enable debugging logging mode at the bottom right of the page and specify a non-standard web socket address.

![settings](https://user-images.githubusercontent.com/13550539/130320607-a493a5df-bbcc-4fb0-a82b-046db45bc952.png)

The settings are saved in the browser's Local Storage and are not lost when the page is refreshed. To reset the settings, remove the keys from Local Storage using Chrome Dev Tools -> Application tab -> Local Storage.

If something is not working as expected, start by enabling debug logging mode.

### Data format

Example of json message for browser (with the list of buses):

```json
{
  "msgType": "Buses",
  "buses": [
    {"busId": "c790сс", "lat": 55.7500, "lng": 37.600, "route": "120"},
    {"busId": "a134aa", "lat": 55.7494, "lng": 37.621, "route": "670к"}
  ]
}
```

Those buses that were not in the list of `buses` of the last message from the server will be removed from the map.

The frontend tracks the user's movement on the map and sends the new window coordinates to the server:

```json
{
  "msgType": "newBounds",
  "data": {
    "east_lng": 37.65563964843751,
    "north_lat": 55.77367652953477,
    "south_lat": 55.72628839374007,
    "west_lng": 37.54440307617188
  },
}
```

### Lint

```shell
flake8
```

### Testing

For testing purpose use `harmful_clients.py` running against `server.py`

```shell
python harmful_clients.py
```
