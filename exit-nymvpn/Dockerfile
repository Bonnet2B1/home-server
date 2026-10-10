FROM debian@sha256:3783cc01769c7b2b1b83a5c5ad96c815348e28ed7da68e2e3687004faa906251

ARG NYM_VERSION=2026.12.4
ARG NYM_ARCH=x86_64
ARG NYM_SHA256=17ec7c1d41395328aada6a71633ba11c9a152960d836f00ba6a9792fb0aa76a4

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates \
      curl \
      dbus \
      dbus-bin \
      iproute2 \
      libdbus-1-3 \
      libmnl0 \
      libnftnl11 \
      nftables \
      policykit-1 \
      python3 \
 && rm -rf /var/lib/apt/lists/*

RUN set -eux; \
    curl -fsSL -o /tmp/nym.tar.gz \
      "https://github.com/nymtech/nym-vpn-client/releases/download/nym-vpn-v${NYM_VERSION}/nym-vpn-core-v${NYM_VERSION}_linux_${NYM_ARCH}.tar.gz"; \
    echo "${NYM_SHA256}  /tmp/nym.tar.gz" | sha256sum -c -; \
    mkdir -p /tmp/nymcore; \
    tar -xzf /tmp/nym.tar.gz -C /tmp/nymcore --strip-components=1; \
    find /tmp/nymcore -maxdepth 1 -type f -exec install -m 0755 {} /usr/local/bin/ \; ; \
    rm -rf /tmp/nym.tar.gz /tmp/nymcore; \
    nym-vpnd --version

# Le client tailscale est necessaire ici pour une seule chose : demander a
# tailscaled quel port wireguard il ouvre. Ce port change a chaque redemarrage,
# et le superviseur doit donc le relire, pas le deviner.
# Le binaire vient de l image alpine de tailscale. Il tourne sur cette base
# debian, verifie. Le socket tailscaled est partage par volume.
COPY --from=local/tailscale-nft:1.102.5 /usr/local/bin/tailscale /usr/local/bin/tailscale

COPY nym-entrypoint.sh /usr/local/bin/nym-entrypoint
COPY 49-nymvpn.rules /etc/polkit-1/rules.d/49-nymvpn.rules

RUN chmod 0755 /usr/local/bin/nym-entrypoint

WORKDIR /root

ENTRYPOINT ["/usr/local/bin/nym-entrypoint"]