{% set base = pillar[pillar['base_name']] %}

update:
  module.run:
    - name:  clouder.base_update
    - host: {{ base['host'] }}
    - m_name: {{ base['name'] }}
    - user: {{ base['user'] }}
    - password: {{ base['password'] }}