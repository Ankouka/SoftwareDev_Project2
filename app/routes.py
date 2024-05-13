'''
CS3250 - Software Development Methods and Tools - Fall 2023
Instructor: Thyago Mota
Student: 
Description: Project 2 - Queen Soopers Web App
'''
from flask import flash
from app import app, db, load_user, cache
from app.square import square, get_latest_orders, get_order
from app.models import User, Order
from app.forms import SignUpForm, SignInForm
from flask import render_template, redirect, url_for, request
from flask_login import login_required, login_user, logout_user, current_user
import bcrypt, uuid
import csv
from datetime import datetime
from matplotlib.figure import Figure
from io import BytesIO
import base64
from flask import current_app






@app.route('/')
@app.route('/index')
@app.route('/index.html')
def index():
    return render_template('index.html')


@app.route('/users/signin', methods=['GET', 'POST'])
def users_signin():
    form = SignInForm()
    errors = []

    if form.validate_on_submit():
        user = db.session.query(User).filter_by(id=form.id.data).first()
        if user and bcrypt.checkpw(form.passwd.data.encode('utf-8'), user.passwd):

            login_user(user)
            return redirect(url_for('orders'))
        else:
            errors = [field.errors[0] for field in form if field.errors]
            flash('Invalid ID or password. Please try again.', 'error')
    return render_template('signin.html', form=form, errors=errors)


@app.route('/users/signup', methods=['GET', 'POST'])
def users_signup():
    form = SignUpForm()
    if form.validate_on_submit():
        passwd = form.passwd.data
        passwd_confirm = form.passwd_confirm.data
        if passwd == passwd_confirm:
            hashed = bcrypt.hashpw(passwd.encode('utf-8'), bcrypt.gensalt())
        else:
            return '<p> Passwords do not match, try again. </p>'
        body = {
            "idempotency_key": str(uuid.uuid4()),
            "family_name": form.family_name.data,
            "given_name": form.given_name.data,
            "email_address": form.email_address.data,
        }
        result = square.customers.create_customer(body)
        try:
            result.body["customer"]["id"]
        except:
            flash('Invalid email address. Please try again.', 'error')
            return render_template('signup.html', form=form)
        if db.session.query(User).filter_by(id=form.id.data).first() != None:
            flash('ID already exists. Please try again.', 'error')
            return render_template('signup.html', form=form)
        if result.is_success:
            new_user = User(
                id=form.id.data,
                customer_id=result.body["customer"]["id"],
                passwd=hashed
            )
            db.session.add(new_user)
            db.session.commit()

            # Log in the newly created user
            login_user(new_user)

            return render_template('User_id_success.html', form=form, user=current_user)

        return '<p>Error creating customer.</p>'
    else:
        return render_template('signup.html', form=form)


@login_required
@app.route('/users/signout', methods=['GET', 'POST'])
def users_signout():
    logout_user()
    return redirect(url_for('index'))

@login_required
@app.route('/orders')
def orders():
    print("Current User ID:", current_user.id)
    user_id = current_user.customer_id
    user_orders = get_latest_orders(user_id)
    order_data = []

    for order in user_orders:
        try:
            # Accessing order information using appropriate indices
            order_id = order['id']
            created_at = order['metadata']['created_at']
            # Assuming 'created_at' is a key in the order metadata

            order_data.append({
                'order_id': order_id,
                'created_at': created_at,
            })

        except (KeyError, ValueError) as e:
            # Handle the case where the expected keys are not present in the order
            # or there is an issue with date formatting
            print(f"Error processing order: {e}. Skipping this order.")

    print("Order Data for /orders route:", order_data)
    return render_template('orders.html', orders=user_orders, user=current_user, order_data=order_data)


@login_required
@app.route('/orders/<id>')
@cache.cached()
def order(id):
    user_id = current_user.id
     # Check if the order information is in the cache
    cache_key = f'order_{user_id}_{id}'
    orders = cache.get(cache_key)
   

    if orders is None:
        # If cache miss, retrieve order information from Square
        orders_from_square = get_order(id)
        
        if orders_from_square is not None:
            # Store orders from Square in the cache for future use
            customer_id = orders_from_square.get('customer_id')
            if customer_id == current_user.customer_id:
                cache.set(f'order_{id}', orders_from_square)
                message = None
                orders = orders_from_square
        else:
            message = "Failed to retrieve order information from Square"
    else:
        
        message = None

    return render_template('order_details.html', message=message, orders=orders, user=current_user,order=orders)

@login_required
@app.route('/orders/summary table', methods=['GET', 'POST'])
def total_price_per_month():
    user_id = current_user.id
    customer_id = current_user.customer_id

    # Use a unique cache key based on user and customer ID
    cache_key = f'orders_{user_id}_{customer_id}'
    force_refresh = request.method == 'POST'  # Check if the request is a POST (e.g., refresh button clicked)

    # Function to retrieve orders either from cache or Square
    def get_orders():
        cached_orders = cache.get(cache_key)
        if cached_orders is not None and not force_refresh:
            return cached_orders
        else:
            latest_orders = get_latest_orders(current_user.customer_id)
            if latest_orders is not None:
                cache.set(cache_key, latest_orders)
                return latest_orders
            else:
                return []

    # Retrieve orders
    orders = get_orders()

    # Process orders to create monthly_spending_data and order_data
    monthly_spending_data = {}
    order_data = []

    for order in orders:
        try:
            # Process the order and accumulate data
            created_at = order['metadata']['created_at']
            month = datetime.strptime(created_at, '%m/%d/%y').strftime('%Y-%m')
            items = order.get('line_items', [])

            total_order_amount = 0.0
            formatted_month = datetime.strptime(created_at, '%m/%d/%y').strftime('%m/%y')

            for item in items:
                amount_spent = item.get('base_price_money', {}).get('amount')
                if amount_spent is not None and isinstance(amount_spent, (int, float)):
                    amount = float(amount_spent)
                    total_order_amount += float(amount)

            total_order_amount_rounded = round(total_order_amount, 2)

            if month in monthly_spending_data:
                monthly_spending_data[month] += total_order_amount_rounded
            else:
                monthly_spending_data[month] = total_order_amount_rounded

            order_data.append({
                'order_id': order['id'],
                'created_at': formatted_month,
                'total_order_amount_rounded': total_order_amount_rounded
            })
        except (KeyError, ValueError) as error:
            print(f"Error processing order: {error}. Skipping this order.")

    datas = fetch_monthly_price()
    # Check if datas is a dictionary
    if isinstance(datas, dict):
        # Sort the dictionary keys in reverse order
        sorted_months = sorted(datas.keys(), key=lambda x: datetime.strptime(x, "%m/%Y"))

        figure = Figure()
        ax = figure.subplots()
        ax.plot(sorted_months, [datas[month] for month in sorted_months])
        ax.set_title("Monthly Spending")
        ax.set_xlabel("Month")
        ax.set_ylabel("Cost in Dollars")

        buf = BytesIO()
        figure.savefig(buf, format="png")
        data = base64.b64encode(buf.getbuffer()).decode("ascii")

        return render_template('total_price_per_month.html', monthly_spending_data=monthly_spending_data, order_data=order_data, monthly_plot=data)
    else:
        # Handle the case where datas is not a dictionary
        return render_template('total_price_per_month.html', monthly_spending_data=monthly_spending_data, order_data=order_data, monthly_plot=None)


@login_required
@app.route('/orders/summary graph', methods=['GET', 'POST'])
def fetch_monthly_price():
     # Instead of reading from the CSV, fetch data from Square API
    user_id = current_user.customer_id
    user_orders = get_latest_orders(user_id)

    monthly_price = {}
    total_price = 0
    current_month = None

    for order in user_orders:
        try:
            date_str = order['metadata']['created_at']
            date = datetime.strptime(date_str, '%m/%d/%y')
            month = date.month
            year = date.year

            if current_month is not None and current_month != month:
                month_year = f'{current_month}/{year}'
                actual_price = round(total_price, 2)
                monthly_price[month_year] = actual_price
                total_price = 0

            month_year = f'{month}/{year}'
            current_month = month
            total_price += float(order['total_money']['amount']) / 100.0  # Amount is in cents, convert to dollars

        except (KeyError, ValueError) as e:
            print(f"Error processing order: {e}. Skipping this order.")

    # Handle the last month
    if current_month is not None:
        month_year = f'{current_month}/{year}'
        actual_price = round(total_price, 2)
        monthly_price[month_year] = actual_price

    
    print("Monthly price: ", monthly_price)
    print("Total price: ", sum(monthly_price.values()))

    return monthly_price

@login_required
@app.route('/orders/most/purchased', methods=['GET', 'POST'])
def most_purchased():
    user_id = current_user.customer_id
    user_orders = get_latest_orders(user_id)
    # Dictionary to store item information
    item_data = {}

    for order in user_orders:

        try:
            # Process the order and accumulate data
            line_items = order.get('line_items', [])
            
            for item in line_items:
                upc = item.get('metadata', {}).get('upc', None)
                name = item.get('name', None)
                paid = item.get('base_price_money', {}).get('amount', None)
            
                # Check if 'paid' is not None before converting to float
                price = float(paid) / 100.0 if paid is not None else 0.0

                if upc is not None and name is not None:
                    # Use get with default value to handle missing UPC in the dictionary
                        item_info = item_data.get(upc,{ 'upc':upc, 'name': name, 'times_purchased': 0, 'total_price': price})
                       
                        # If item already exists, update the count, total price, and quantity
                        item_info['times_purchased'] += 1
                    
                        # Update or add the item_info to the dictionary
                        item_data[upc] = item_info

        except (KeyError, ValueError) as e:
            print(f"Error processing order: {e}. Skipping this order.")

    print("Item data in most_purchased route:", item_data)
    # Convert the dictionary to a list for sorting
    sorted_items = sorted(item_data.values(), key=lambda x: x['times_purchased'], reverse=True)[:5]

    print("Items in most_purchased route:", sorted_items)
    return render_template('most_purchased.html', items=sorted_items, user=current_user)

@login_required
@app.route('/orders/most/expensive', methods=['GET', 'POST'])
def most_expensive():
    print('Most Expensive')
    user_id = current_user.customer_id
    user_orders = get_latest_orders(user_id)
    most_expensive_items = {}

    for order in user_orders:

        try:
            # Process the order and accumulate data
            line_items = order.get('line_items', [])
            
            for item in line_items:
                upc = item.get('metadata', {}).get('upc', None)
                name = item.get('name', None)
                paid = item.get('base_price_money', {}).get('amount', None)
            
                # Check if 'paid' is not None before converting to float
                price = float(paid) / 100.0 if paid is not None else 0.0

                if upc is not None and name is not None:
                    # Use get with default value to handle missing UPC in the dictionary
                        item_info = most_expensive_items.get(upc,{ 'upc':upc, 'name': name, 'times_purchased': 0, 'total_price': price})
                       
                        item_info['times_purchased'] += 1
                         # If the current item's price is greater, update the information
                        if price > item_info['total_price']:
                            item_info['total_price'] = price
                            
                    
                        # Update or add the item_info to the dictionary
                        most_expensive_items[upc] = item_info

        except (KeyError, ValueError) as e:
            print(f"Error processing order: {e}. Skipping this order.")

    print("Item data in most_purchased route:", most_expensive_items)
    # Convert the dictionary to a list for sorting
    sorted_items = sorted(most_expensive_items.values(), key=lambda x: x['total_price'], reverse=True)[:5]

    print("Items in most_purchased route:", sorted_items)
    return render_template('most_expensive.html', items=sorted_items, user=current_user)