
{% set container = pillar[pillar['container_name']] %}

{% if not 'secretkey' in pillar or pillar.secretkey == container['secretkey'] %}

include:
  - container_purge

{% if 'build' in pillar %}

copy:
  file.recurse:
    - name: /tmp/salt_build/build_{{ pillar['image'] }}
    - source: salt://containers/build_{{ pillar['container_name'] }}

build:
  dockerng.image_present:
    - name: {{ pillar['image'] }}
    - build: /tmp/salt_build/build_{{ pillar['image'] }}

clean:
  file.absent:
    - name: /tmp/salt_build/build_{{ pillar['image'] }}

{% endif %}

deploy:
  dockerng.running:
    - name: {{ pillar['container_name'] }}
    - image: {{ pillar['image'] }}
    - detach: True
    - tty: True
    - restart_policy: always
    - port_bindings: {{ container['ports'] }}
    - binds:  {{ container['volumes'] }}
    - volumes_from:  {{ container['volumes_from'] }}
    - links:  {{ container['links'] }}
    - environment: {{ container['environment'] }}


{% if 'update_bases' in pillar %}
{% for base_name in container['bases'] %}

{% do pillar.update({'base_name': base_name}) %}

{% set base = pillar[pillar['base_name']] %}

update:
  module.run:
    - name:  clouder.base_update
    - host: {{ base['host'] }}
    - m_name: {{ base['name'] }}
    - user: {{ base['user'] }}
    - password: {{ base['password'] }}

{% endfor %}
{% endif %}


{% endif %}
