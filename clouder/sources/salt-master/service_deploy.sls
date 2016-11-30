
{% set service = pillar[pillar['service_name']] %}

{% if not 'secretkey' in pillar or pillar.secretkey == service['secretkey'] %}

include:
  - service_purge

{% if 'build' in pillar %}

copy:
  file.recurse:
    - name: /tmp/salt_build/build_{{ pillar['image'] }}
    - source: salt://services/build_{{ pillar['service_name'] }}

pull:
  dockerng.image_present:
    - name: {{ service['from'] }}
    - force: True

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
    - name: {{ pillar['service_name'] }}
    - image: {{ pillar['image'] }}
    - detach: True
    - tty: True
    - restart_policy: always
    - port_bindings: {{ service['ports'] }}
    - binds:  {{ service['volumes'] }}
    - volumes_from:  {{ service['volumes_from'] }}
    - links:  {{ service['links'] }}
    - environment: {{ service['environment'] }}


{% if 'update_bases' in pillar %}
{% for base_name in service['bases'] %}

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
