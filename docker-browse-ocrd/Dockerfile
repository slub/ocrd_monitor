FROM python:3.7

RUN apt-get update \
    && apt-get install -y --no-install-recommends libcairo2-dev libgtk-3-bin libgtk-3-dev libglib2.0-dev libgtksourceview-3.0-dev libgirepository1.0-dev gir1.2-webkit2-4.0 pkg-config cmake \
    && pip3 install -U setuptools \
    && pip3 install browse-ocrd

ENV GDK_BACKEND broadway
ENV BROADWAY_DISPLAY :5

EXPOSE 8085

COPY init.sh /init.sh

RUN chmod +x /init.sh

CMD ["/init.sh"]