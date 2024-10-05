from flask import Flask, request, render_template, jsonify
import pandas as pd
import os

app = Flask(__name__)

# Route to render the main page
@app.route('/')
def index():
    return render_template('index.html')

# Route to handle CSV file upload and data processing
@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return "No file part", 400
    file = request.files['file']
    if file.filename == '':
        return "No selected file", 400
    if file:
        # Save and process the CSV file
        filepath = os.path.join('uploads', file.filename)
        file.save(filepath)
        if file.filename.startswith('Discover'):
            data = pd.read_csv(filepath, on_bad_lines='skip', engine='python')
            processed_data = process_data(data, file_type='discover')
        elif file.filename.startswith('Apple'):
            data = pd.read_csv(filepath, on_bad_lines='skip', engine='python')
            processed_data = process_data(data, file_type='apple')
        else:
            data = pd.read_csv(filepath, skiprows=7, on_bad_lines='skip', engine='python')  # Skip the first 7 rows to reach the data
            processed_data = process_data(data, file_type='main')
        return jsonify(processed_data)

# Function to process CSV data and calculate totals
def process_data(data, file_type):
    if file_type == 'discover':
        # Rename columns to match expected format
        data = data[['Trans. Date', 'Description', 'Amount']]
        data.rename(columns={'Trans. Date': 'date', 'Description': 'description', 'Amount': 'amount'}, inplace=True)
        # Convert 'date' column to datetime and 'amount' to numeric
        data['date'] = pd.to_datetime(data['date'], errors='coerce')
        data['amount'] = pd.to_numeric(data['amount'], errors='coerce')
        # Keep only positive amounts (payments)
        data = data[data['amount'] > 0]
    elif file_type == 'apple':
        # Select relevant columns and rename to match expected format
        data = data[['Transaction Date', 'Description', 'Amount (USD)']]
        data.rename(columns={'Transaction Date': 'date', 'Description': 'description', 'Amount (USD)': 'amount'}, inplace=True)
        # Convert 'date' column to datetime and 'amount' to numeric
        data['date'] = pd.to_datetime(data['date'], errors='coerce')
        data['amount'] = pd.to_numeric(data['amount'], errors='coerce')
        # Keep only positive amounts (payments)
        data = data[data['amount'] > 0]
    else:
        # Rename columns to match expected format (main CSV)
        data.columns = ['date', 'description', 'amount', 'running_total']
        data = data[['date', 'description', 'amount']]
        # Convert 'date' column to datetime and 'amount' to numeric
        data['date'] = pd.to_datetime(data['date'], errors='coerce')
        data['amount'] = pd.to_numeric(data['amount'], errors='coerce')
        # Keep only negative amounts (expenses) and make them positive
        data = data[data['amount'] < 0]
        data['amount'] = data['amount'].abs()
    
    # Drop rows with missing description or amount
    data.dropna(subset=['description', 'amount'], inplace=True)
    
    # Create a complete date range from the minimum to maximum date in the dataset
    full_date_range = pd.date_range(start=data['date'].min(), end=data['date'].max())
    
    # Group by date and calculate total expenses per date
    grouped = data.groupby(data['date'].dt.strftime('%Y-%m-%d')).agg(total_amount=('amount', 'sum'))
    grouped = grouped.reindex(full_date_range.strftime('%Y-%m-%d'), fill_value=0)
    
    items = data.groupby(data['date'].dt.strftime('%Y-%m-%d'))[['description', 'amount']].apply(lambda x: x.to_dict('records')).to_dict()
    
    result = {
        'dates': grouped.index.tolist(),
        'totals': grouped['total_amount'].tolist(),
        'items': items
    }
    return result

if __name__ == '__main__':
    if not os.path.exists('uploads'):
        os.makedirs('uploads')
    app.run(debug=True)