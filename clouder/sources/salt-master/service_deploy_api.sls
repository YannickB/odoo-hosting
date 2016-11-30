{% set postdata = data.get('post', {}) %}

service deploy:
  local.state.apply:
    - tgt: {{ postdata.tgt }}
    - arg:
      - service_deploy
    - kwarg:
        pillar:
          service_name: {{ postdata.service_name }}
          image: {{ postdata.image }}
          secretkey: {{ postdata.secretkey }}
          update_bases: True