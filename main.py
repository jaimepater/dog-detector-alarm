import machine
import time
from umqtt_simple import MQTTClient
import network
import ussl
import ntptime
import secrets

# Define GPIO pins
GPIO0 = machine.Pin(0, machine.Pin.OUT)
GPIO1 = machine.Pin(1, machine.Pin.OUT)
GPIO2 = machine.Pin(2, machine.Pin.OUT)
GPIO3 = machine.Pin(3, machine.Pin.OUT)

# WiFi settings
WIFI_SSID = secrets.wifi_ssid
WIFI_PASSWORD = secrets.wifi_password
MQTT_USER = secrets.mqtt_user
MQTT_BROKER = secrets.mqtt_broker
MQTT_PASSWORD = secrets.mqtt_password
MQTT_PORT = secrets.mqtt_port
MQTT_TOPIC = secrets.mqtt_topic

wlan = network.WLAN(network.STA_IF)

def led_init():
    GPIO0.off()
    GPIO1.off()
    GPIO2.off()
    GPIO3.off()


def wifi():
    print('----------------------------------------------------------------------------------------------')
    print('Connecting to AP: ' + WIFI_SSID )
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    connected = False
    attempt = 0
    while not connected and attempt < 10:
        attempt += 1
        if wlan.status() < 0 or wlan.status() >= 3:
            connected = True
        if not connected:
            print("Connection attempt failed: " + str(attempt))
            time.sleep(1)
        else:
            print("Connected on attempt: " + str(attempt))
    if not connected or wlan.ifconfig()[0] == "0.0.0.0":
        print("Bad WiFi connection: " + wlan.ifconfig()[0])
        while True:
            GPIO0.off()
            time.sleep_ms(150)
            GPIO0.on()
            time.sleep_ms(150)        
    print("WiFi status: " + str(wlan.ifconfig()))
    print('----------------------------------------------------------------------------------------------')
    print('Connecting to NTP')
    ntptime.host = "de.pool.ntp.org"
    ntptime.settime()
    print('Current time: ' + str(time.localtime()))
    GPIO0.on()
    
def get_certificate():
    print('Loading CA Certificate')
    with open("/cert/hivemq-com-chain.der", 'rb') as f:
        cacert = f.read()
        f.close()
    print('Obtained CA Certificate')
    return cacert

def connect_to_mqtt(cert):
    print('----------------------------------------------------------------------------------------------')
    print("Connecting to " + MQTT_BROKER + " as user " + MQTT_USER)
    sslparams = {'server_side': False,
             'key': None,
             'cert': None,
             'cert_reqs': ussl.CERT_REQUIRED,
             'cadata': cert,
             'server_hostname': MQTT_BROKER}
    client = MQTTClient(client_id="picow",
                    server=MQTT_BROKER,
                    port=MQTT_PORT,
                    user=MQTT_USER,
                    password=MQTT_PASSWORD,
                    keepalive=0,
                    ssl=True,
                    ssl_params=sslparams)
    client.set_callback(on_message)
    client.DEBUG = True
    client.connect(False)
    GPIO1.on()
    GPIO2.on()
    print('Connected to MQTT Broker: ' + MQTT_BROKER)
    client.subscribe(MQTT_TOPIC)
    return client


def reconnect_wifi():
    if not wlan.isconnected():
        print('WiFi connection lost, attempting to reconnect')
        wifi()
    else:
       GPIO0.on() 

def reconnect_mqtt(client, cert):
    try:
        t = client.ping()
        GPIO1.on()
        GPIO2.on()
        return client 
    except:
        client.disconnect()
        print('MQTT connection lost, attempting to reconnect')
        return connect_to_mqtt(cert)
        


def on_message(topic, msg):
    print("Received message: ", msg)
    GPIO3.on()
    GPIO2.off()
    time.sleep(900)  
    GPIO3.off()  
    GPIO2.on() 

led_init()
wifi()
cert = get_certificate()
client = connect_to_mqtt(cert)
with open('/exceptions.txt', 'w') as f:
    while True:
        try:
            client.check_msg()
            reconnect_wifi()
            client = reconnect_mqtt(client, cert)  
            client.check_msg()
        except Exception as e:
             print(e)
             led_init()
             # 'a' mode will append to the file
             f.write(str(e) + '\n')  # convert the exception to a string and write to the file