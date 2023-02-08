# simple-web-server

* A simple Python web server that follows the HTTP 1.0 Protocol

## What can it do?
* Receieve as well as respond to GET requests.
* Establish both persistent and non-persistent TCP connections with clients.
* Log the time as well as any relevant information to requests.
* Respond with requested files if they exist.
* Maintain silmutaneous connections to clients.

## How can you test it?

### Terminal 1 - Server
```
Python3 webserver.py [ip] [port]
```
This starts the webserver.

### Terminal 2 - Client
```
nc [ip] [port]
```
Starts communication

```
GET /[file] HTTP/1.0
Connection: keep-alive
```
Initalizes socket with persistent connection and will respond with file if it exists.

```
GET /[file] HTTP/1.0
Connection: closed
```
Initalizes socket with non-persistent connection and will respond with file if it exists.

## What does it utilize?
* socket module to establish connection.
* os module to determine if file exists that client is requesting.
* time module for logging time of requests.
