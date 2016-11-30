include:
  - service_stop

start:
  module.run:
    - name: dockerng.start
    - args:
      - {{ pillar['service_name'] }}