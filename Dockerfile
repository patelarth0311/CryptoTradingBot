# syntax=docker/dockerfile:1

FROM python:3.9

RUN pip install pandas
RUN pip install ccxt
RUN pip install matplotlib

RUN mkdir -p /home/app

COPY . /home/app

CMD python3 home/app/binance.py