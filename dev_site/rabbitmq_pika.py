#!/usr/bin/env python
import time
import pika
import pika.exceptions
import octo.config_cred as conf_cred


def main_check():
    credentials = pika.PlainCredentials(
        username=conf_cred.cred['rabbitmq_user'],
        password=conf_cred.cred['rabbitmq_pswd'],
    )
    parameters = pika.ConnectionParameters(
        host='localhost',
        port=5672,
        virtual_host='tentacle',
        credentials=credentials,
    )

    w_routines = 'w_routines@tentacle.dq2'
    routing_key = 'w_routines@tentacle.dq2'

    # url_params = pika.connection.URLParameters(conf_cred.cred['rabbitmq_url'])
    connection = pika.BlockingConnection(parameters=parameters)
    print(f'is_open: {connection.is_open}')

    channel = connection.channel()
    channel.exchange_declare(exchange=w_routines, exchange_type='direct', durable=True)
    queue_declare = channel.queue_declare(queue=w_routines, passive=True)
    channel.queue_bind(exchange=w_routines, queue=w_routines, routing_key=routing_key)
    channel.confirm_delivery()

    def on_delivery_confirmation(method_frame):
        confirmation_type = method_frame.method.NAME.split('.')[1].lower()
        if confirmation_type == 'ack':
            print('message published')
        elif confirmation_type == 'nack':
            print('message not routed')

    for i in range(20):
        try:
            channel.basic_publish(
                exchange=w_routines,
                routing_key=routing_key,
                body=f'Sending message to w_routines@tentacle.dq2',
                properties=pika.BasicProperties(content_type='text/plain', delivery_mode=2),
                # mandatory=True,
            )
            print('Message was published')
        except pika.exceptions.UnroutableError:
            print('Message was returned')

    # Close the channel and the connection

    print(f'queue_declare {queue_declare}')
    print(f'Messages len {queue_declare.method.message_count}')

    channel.close()
    connection.close()
    print(f'is_closed: {connection.is_closed}')


class RabbitCheck():

    def __init__(self):
        self.connection = None
        self.channel = None
        self.connect()

    def connect(self):
        credentials = pika.PlainCredentials(username=conf_cred.cred['rabbitmq_user'], password=conf_cred.cred['rabbitmq_pswd'])
        parameters = pika.ConnectionParameters(host='localhost', port=5672, virtual_host='tentacle', credentials=credentials)
        self.connection = pika.BlockingConnection(parameters=parameters)
        self.channel = self.connection.channel()

    def connection_close(self):
        self.channel.close()
        self.connection.close()

    def declare_exchange_queue(self, queue_name, exchange_name, routing_key):
        self.channel.exchange_declare(exchange=exchange_name, exchange_type='direct', durable=True)
        queue_declare = self.channel.queue_declare(queue=queue_name, passive=True)
        self.channel.queue_bind(exchange=exchange_name, queue=queue_name, routing_key=routing_key)
        self.channel.confirm_delivery()
        return queue_declare

    def declare_queue(self, queue_name):
        return self.channel.queue_declare(queue=queue_name, passive=True)

    def queue_count(self, queue_name, queue_declare=None):
        if not queue_declare:
            queue_declare = self.declare_queue(queue_name)
        queue_len = queue_declare.method.message_count
        return queue_len

    def queue_count_list(self, queues_list):
        queues_d = dict()
        for queue in queues_list:
            queue_len = self.queue_count(queue_name=queue)
            queues_d.update({queue:queue_len})
        return queues_d

    def message_pub(self, queue_name, exchange_name, routing_key, body):
        self.declare_exchange_queue(queue_name, exchange_name, routing_key)
        try:
            self.channel.basic_publish(
                exchange=exchange_name,
                routing_key=routing_key,
                body=body,
                properties=pika.BasicProperties(content_type='text/plain', delivery_mode=2),
                # mandatory=True,
            )
            print('Message was published')
        except pika.exceptions.UnroutableError:
            print('Message was returned')

for i in range(5):
    RabbitCheck().message_pub(
        queue_name='w_routines@tentacle.dq2',
        exchange_name='w_routines@tentacle.dq2',
        routing_key='task.test',
        body='Test task adding messages!'
    )


queues_list = ['alpha@tentacle.dq2', 'w_parsing@tentacle.dq2', 'w_routines@tentacle.dq2']
all_queues_len = RabbitCheck().queue_count_list(queues_list)
print(all_queues_len)