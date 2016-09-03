stop:
  dockerng.stopped:
    - name: {{ pillar['container_name'] }}
