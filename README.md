# HTTP API for Unifi Controller guest vouchers

Simple Flask app that exposes an HTTP API to requests guest vouchers from a Unifi Controller with hotspot enabled.



## Run the app
~~~~
docker run -d -p 5000:5000 -e HTTP_USER= \
                -e HTTP_PASS= \
                -e UNIFI_HOTSPOT_USER= \
                -e UNIFI_HOTSPOT_PASS= \
                -e UNIFI_URL= \
                -e VERIFY_CERT=False \
                namendez/unifi-vouchers-http-api
~~~~

Requests are authenticated with basic auth, using the user and pass provided to HTTP_USER and HTTP_PASS.

## Example request
~~~~
curl -X POST \
  http://localhost:5000/api/voucher \
  -H 'Authorization: Basic YWRtaW46YWRtaW4=' \
  -H 'content-type: multipart/form-data' \
  -F voucher_duration=90 \
  -F unit=days \
  -F 'note=test note'
~~~~

## Example response
~~~~
{
    "voucher_code": "1116039522"
}
~~~~

## Dockerhub

Link to [Dockerhub](https://hub.docker.com/r/namendez/unifi-vouchers-http-api) repo.