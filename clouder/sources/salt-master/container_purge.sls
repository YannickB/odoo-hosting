include:
  - container_stop

purge:
  module.run:
    - name: dockerng.rm
    - args:
      - {{ pillar['container_name'] }}
    - kargs:
      - volumes = True