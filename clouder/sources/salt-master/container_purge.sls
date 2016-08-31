include:
  - container_stop

purge:
  module.run:
    - name: dockerng.rm
    - args:
      - {{ pillar['name'] }}
    - kargs:
      - volumes = True