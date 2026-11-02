"""Run on the host: python client.py [http://localhost:5000]."""
import json
import sys
from common import call
base = sys.argv[1] if len(sys.argv)>1 else 'http://localhost:5000'
for path, method in [('/search/distributed%20systems','GET'), ('/search/undergraduate%20school','GET'), ('/info/2','GET'), ('/purchase/2','POST'), ('/info/2','GET')]:
    result, status = call(base+path, method)
    print(method, path, '->', status)
    print(json.dumps(result, indent=2))
    if 'message' in result:
        print(result['message'])
