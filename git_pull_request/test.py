from urllib import parse


url = "http://abd:80/jdksf"
parsed = parse.urlparse(url)
if parsed.scheme == "https": # not empty scheme usually is https
    path = parsed.path.strip("abc")
    c = str('dsfkljf')
