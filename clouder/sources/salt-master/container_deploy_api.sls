{% set postdata = data.get('post', {}) %}

container deploy:
  local.state.apply:
    - tgt: {{ postdata.tgt }}
    - arg:
      - container_deploy
    - kwarg:
        pillar:
          container_name: {{ postdata.container_name }}
          image: {{ postdata.image }}
          secretkey: {{ postdata.secretkey }}
          update_bases: True