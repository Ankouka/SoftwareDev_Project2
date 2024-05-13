'''
CS3250 - Software Development Methods and Tools - Fall 2023
Instructor: Thyago Mota
Student:
Description: Project 2 - Queen Soopers Web App
'''

import os
from square.client import Client

square = Client(
    access_token=os.environ['SQUARE_ACCESS_TOKEN'],
    environment='sandbox')

# returns the latest orders given the id of a customer
def get_latest_orders(customer_id):
    try:
        response = square.orders.search_orders(body={
            "location_ids": ['L9VRXX1AEC7KY'],
            "query": {
                "filter": {
                    "customer_filter": {
                        "customer_ids": [customer_id]
                    }
                }
            },
            "sort": {
                "sort_field": "CREATED_AT",  # Sort by creation date
                "sort_order": "DESC"  # Sort in descending order (most recent first)
            },
            "limit": 100  # Specify the number of orders you want to retrieve
        })

        if 'orders' in response.body:
            orders = response.body['orders']
            return orders
        else:
            print("Unexpected response format. Missing 'orders' key.")
            return []
    except Exception as e:
        print(f"Error retrieving latest orders from Square: {e}")
        return []

# returns an order given its id
def get_order(order_id):
    try:
        response = square.orders.retrieve_order(order_id)

        print("Square API Request:", response.request)
        print("Square API Response:", response.body)


        # Check if the response was successful
        if response.is_success():
            # Access the order information
            order = response.body.get('order', None)
            print(response)
            return order
        else:
            print(f"Square API error: {response.errors}")
            return None
    except Exception as e:
        # Handle errors, log them, etc.
        print(f"Error retrieving order from Square: {e}")
        return None
