# SWS
SWS imitates Nginx's handling of GET requests. SWS can handle persistant, and non-persistant connections, as well as requesting multiple objects via piping. 

## Running SWS
To start the SWS server, navigate to the directory containing the sws.py file and run the following command in your terminal or command prompt:
```python3 sws.py <address> <port>```

# Example
To run SWS on localhost and port 8080, use:
```python3 sws.py localhost 8080```
This command starts the server on your local machine, making it accessible via http://localhost:8080 in your web browser.

# Requesting Objects
From another terminal connect to the address and port via netcat,
```nc <address> <port>```, and start requesting objects!
