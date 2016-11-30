include:
  - service_stop

purge:
  module.run:
    - name: dockerng.rm
    - args:
      - {{ pillar['service_name'] }}
    - kargs:
      - volumes = True