include:
  - container_stop

start:
  module.run:
    - name: dockerng.start
    - args:
      - {{ pillar['name'] }}