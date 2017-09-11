from app import app

if __name__ == '__main__':
    context = ('localhost.cert', 'localhost.key')
    app.run(host='127.0.0.1', port=5000, ssl_context=context, debug=True, threaded=True)
