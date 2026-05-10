"""
Flask web application for cross-journal search
"""

from flask import Flask, render_template, request, jsonify
from search_engine import SearchEngine

app = Flask(__name__)
search_engine = SearchEngine()


@app.route('/')
def index():
    """Render the main search page"""
    journals = search_engine.get_available_journals()
    return render_template('index.html', journals=journals)


@app.route('/search', methods=['POST'])
def search():
    """Handle search requests"""
    data = request.get_json()
    keywords = data.get('keywords', '')
    sort_by = data.get('sort_by', 'year')  # Default: sort by year

    if not keywords:
        return jsonify({'error': 'Keywords are required'}), 400

    try:
        results = search_engine.search(keywords, sort_by=sort_by)
        return jsonify({
            'success': True,
            'count': len(results),
            'results': results
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/journals', methods=['GET'])
def get_journals():
    """Get list of available journals"""
    journals = search_engine.get_available_journals()
    return jsonify({'journals': journals})


if __name__ == '__main__':
    print("\n" + "="*60)
    print("Cross-Journal Search System for Management Studies")
    print("="*60)
    print("\nAvailable Journals:")
    for i, journal in enumerate(search_engine.get_available_journals(), 1):
        print(f"  {i}. {journal}")
    print("\nStarting web server...")
    print("Access the application at: http://localhost:5000")
    print("="*60 + "\n")

    app.run(debug=True, host='0.0.0.0', port=5000)
