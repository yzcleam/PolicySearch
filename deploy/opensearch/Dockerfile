ARG OPENSEARCH_BASE_IMAGE=m.daocloud.io/docker.io/opensearchproject/opensearch:2.19.3
FROM ${OPENSEARCH_BASE_IMAGE}

COPY --chown=1000:1000 opensearch-analysis-ik-2.19.3.zip /tmp/opensearch-analysis-ik.zip
RUN /usr/share/opensearch/bin/opensearch-plugin install --batch \
      file:///tmp/opensearch-analysis-ik.zip \
    && rm -f /tmp/opensearch-analysis-ik.zip

# The plugin installer drops the jars but not the dictionaries. IK looks for
# them under <OPENSEARCH_HOME>/config/analysis-ik; keep a copy in the plugin
# directory as well for older loader paths.
COPY --chown=1000:1000 ik-config/config /usr/share/opensearch/config/analysis-ik
COPY --chown=1000:1000 ik-config/config /usr/share/opensearch/plugins/opensearch-analysis-ik/config
