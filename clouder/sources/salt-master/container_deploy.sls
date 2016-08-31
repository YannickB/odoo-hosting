include:
  - container_purge

{% set container = pillar[pillar['name']] %}

copy:
  file.recurse:
    - name: /tmp/salt_build/build_{{ pillar['image'] }}
    - source: salt://containers/build_{{ pillar['name'] }}

build:
  dockerng.image_present:
    - name: {{ pillar['image'] }}
    - build: /tmp/salt_build/build_{{ pillar['image'] }}

clean:
  file.absent:
    - name: /tmp/salt_build/build_{{ pillar['image'] }}

deploy:
  dockerng.running:
    - name: {{ pillar['name'] }}
    - image: {{ pillar['image'] }}
    - detach: True
    - tty: True
    - restart_policy: always
    - port_bindings: {{ container['ports'] }}
    - binds:  {{ container['volumes'] }}
    - volumes_from:  {{ container['volumes_from'] }}
    - links:  {{ container['links'] }}
    - environment: {{ container['environment'] }}