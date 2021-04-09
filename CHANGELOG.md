# Changelog for nats-python

## 0.9.0 (20XX-XX-XX)

- Added Python 3.9.* support

## 0.8.0 (2020-06-21)

- Added TSL support, #13 by @nineinchnick

## 0.7.0 (2020-02-15)

- Fixed issue when threads are blocked on close while reading, #11 by @richard78917

## 0.6.0 (2020-01-08)

- Added Python 3.8.* support, #10

## 0.5.0 (2019-08-27)

- Fixed passing of subscription queue name to the NATS server, #3

## 0.4.0 (2018-09-24)

- Use `BytesIO` as read buffer

## 0.3.0 (2018-09-21)

- Improved receive messages logic
- Fixed regex deprecation warnings

## 0.2.0 (2018-09-01)

- Changed subscription ID generation logic from `nuid` to `int`

## 0.1.0 (2018-08-30)

- Initial implementation
