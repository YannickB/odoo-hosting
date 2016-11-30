stop:
  dockerng.stopped:
    - name: {{ pillar['service_name'] }}
