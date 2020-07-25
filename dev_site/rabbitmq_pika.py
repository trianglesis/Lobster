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

def callback_func(channel, method, properties, body):
    print(body)

# main_check()
class RabbitCheck():

    def __init__(self):
        self.queue = None
        self.exchange = None
        self.routing_key = None
        self.username = conf_cred.cred['rabbitmq_user']
        self.password = conf_cred.cred['rabbitmq_pswd']
        self.host = 'localhost'
        self.port = 5672
        self.virtual_host = 'tentacle'

        self.channel_open()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.channel.close()
        self.connection.close()
        print("Disconnected")

    def credentials(self):
        return pika.PlainCredentials(username=self.username, password=self.password)

    def connect_params(self):
        return pika.ConnectionParameters(
            host=self.host,
            port=self.port,
            virtual_host=self.virtual_host,
            credentials=self.credentials(),
        )

    def channel_open(self):
        self.connection = pika.BlockingConnection(parameters=self.connect_params())
        self.channel = self.connection.channel()

    def declare_exchange_queue(self, queue, exchange=None, routing_key=None, create_q=False):
        self.queue = queue
        if not self.queue:
            self.queue = 'default'

        self.exchange = exchange
        if not self.exchange:
            self.exchange = queue

        self.routing_key = routing_key
        if not self.routing_key:
            self.routing_key = queue

        if create_q:
            self.channel.queue_declare(queue=self.queue)
            self.channel.queue_bind(exchange=self.exchange, queue=self.queue, routing_key=self.routing_key)
            self.channel.exchange_declare(exchange=self.exchange, exchange_type='direct')
        else:
            self.channel.queue_declare(queue=self.queue, passive=True)
            self.channel.queue_bind(exchange=self.exchange, queue=self.queue, routing_key=self.routing_key)
            self.channel.exchange_declare(exchange=self.exchange, exchange_type='direct', durable=True)

        self.channel.confirm_delivery()

    def message_pub(self, body, queue=None, exchange=None, routing_key=None, create_q=False):
        self.declare_exchange_queue(queue, exchange, routing_key, create_q=create_q)

        try:
            self.channel.basic_publish(
                exchange=self.exchange,
                routing_key=self.routing_key,
                body=body,
                # properties=pika.BasicProperties(content_type='text/plain', delivery_mode=2),
                # mandatory=True,
            )
            print('Message was published')
        except pika.exceptions.UnroutableError:
            print('Message was returned')

    def declare_queue(self, queue):
        return self.channel.queue_declare(queue=queue, passive=True)

    def queue_count(self, queue, queue_declare=None):
        if not queue_declare:
            queue_declare = self.declare_queue(queue)
        queue_len = queue_declare.method.message_count
        return queue_len

    def queue_count_list(self, queues_list):
        queues_d = dict()
        for queue in queues_list:
            queue_len = self.queue_count(queue=queue)
            queues_d.update({queue:queue_len})
        return queues_d

    def get_message(self, queue):
        method_frame, header_frame, body = self.channel.basic_get(queue=queue)
        # print(f'method_frame {method_frame}, header_frame {header_frame}, body {body}')
        if method_frame is None:
            pass
        else:
            if method_frame.NAME == 'Basic.GetEmpty':
                self.connection.close()
                return False, None
            else:
                return body, method_frame.delivery_tag

    def get_messages_ask(self, queue, body=None, grab_all=False):
        all_messages = []
        all_messages_found = []
        queue_count = self.queue_count(queue)
        for method_frame, properties, body_cons in self.channel.consume(queue=queue):
            # print(f"method_frame {method_frame}, properties {properties} body {body}")
            if body == body_cons.decode('utf-8'):
                # print(f"We've found message in queue: {body_cons}, tag {method_frame.delivery_tag}")
                self.channel.basic_ack(method_frame.delivery_tag)
                all_messages_found.append({'body': body_cons, 'tag': method_frame.delivery_tag, 'ack': True})
            else:
                if grab_all:
                    all_messages.append({'body': body_cons, 'tag': method_frame.delivery_tag, 'ack': False})
                # else:
                    # print(f"Is this we're asking for? No! {body_cons} != {body}")
                # Exit, when reach last message from queue:
                if queue_count == method_frame.delivery_tag:
                    break
        messages = dict(all_messages_found=all_messages_found)
        if grab_all:
            messages.update(all_messages=all_messages)
        return messages

    def get_message_ack(self, queue, body):
        message_body, tag = self.get_message(queue)
        if body in message_body.decode('utf-8'):
            self.channel.basic_ack(delivery_tag=tag)
            self.connection.close()
            return f'Message acknowledged: {body}'
        else:
            return f"There is no message you're asking for! {message_body.decode('utf-8')}"

    def consume(self, queue):
        result = self.declare_queue(queue)
        self.channel.basic_consume(queue, auto_ack=False, on_message_callback=callback_func)
        # self.channel.start_consuming()

"""
https://stackoverflow.com/questions/28550140/python-and-rabbitmq-best-way-to-listen-to-consume-events-from-multiple-channel
"""

# Pub message to queue:
# for i in range(10):
#     RabbitCheck().message_pub(queue='w_routines@tentacle.dq2', body=f'Testing message {i}')
#     # Check all queues by list:
#     queues_list = ['alpha@tentacle.dq2', 'w_parsing@tentacle.dq2', 'w_routines@tentacle.dq2']
#     all_queues_len = RabbitCheck().queue_count_list(queues_list)
#     print(all_queues_len)

# RabbitCheck().message_pub(queue='task_statuses', body=f'p4_sync_finished', create_q=True)
# all_queues_len = RabbitCheck().queue_count_list(['task_statuses'])
# print(all_queues_len)

# message = RabbitCheck().get_message_ack(queue='w_routines@tentacle.dq2', body='Testing message 8')
# print(message)

# message = RabbitCheck().get_messages_ask(queue='w_routines@tentacle.dq2', body='Testing message 1')
# print(message)
