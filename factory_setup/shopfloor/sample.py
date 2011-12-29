# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""This module provides a sample implementation of factory shop floor system.

To use this module, run:
  python shopfloor_server.py -m shopfloor.sample.SampleShopfloor

To create your own module, start with "template.py".
"""

import copy
import logging
import os
import shelve
import time

import shopfloor


class SampleShopFloor(shopfloor.ShopFloorBase):
  """The sample implementation for factory shop floor system.

  This sample system stores everything in a Python dict (and serialized to
  DEFAULT_DATA_STORE_FILE or the file assigned by config param),
  initialized by function _CreateSampleDatabase.
  """
  NAME = 'Sample Implementation (do NOT use for production)'
  VERSION = 1

  DEFAULT_DATA_STORE_FILE = '/tmp/cros_shopfloor.db'

  def __init__(self, config=None):
    """Initializes the sample shop floor server.

    Args:
      config: File path for data store file name.
    """
    logging.info('Shop floor system started.')
    self.data_file = config or self.DEFAULT_DATA_STORE_FILE
    self.data_store = None
    try:
        self.data_store = shelve.open(self.data_file, protocol=2)
    except:
      logging.critical('Invalid data store file: %s', self.data_file)
      raise

    if (('VERSION' not in self.data_store) or
        self.data_store['VERSION'] != self.VERSION):
      logging.info('Re-creating sample data store.')
      self.data_store.clear()
      self.data_store.update(_CreateSampleDatabase())
      self.data_store['VERSION'] = self.VERSION
      self._Flush()

  def _Flush(self):
    """Updates data store into persistent storage."""
    try:
      self.data_store.sync()
    except:
      logging.critical('Failed to flush data store file: %s', self.data_file)
      raise

  def _AppendStatus(self, serial, msg):
    """Appends one message to status log."""
    self.data_store[serial]['status'].append('%s %s' % (
        time.strftime("%Y-%m-%d %H:%M:%S %z"), msg))
    self._Flush()

  def _CheckSerialNumber(self, serial):
    """Checks if given serial number is in data store or not.

    Raises:
      ValueError if serial number is invalid.
    """
    if serial in self.data_store:
      return True
    message = 'Unknown serial number: %s' % serial
    logging.error(message)
    raise ValueError(message)

  def GetHWID(self, serial):
    """See help(ShopFloorBase.GetHWID)"""
    logging.debug('GetHWID(%s)', serial)
    self._CheckSerialNumber(serial)

    self._AppendStatus(serial, 'GetHWID')
    return self.data_store[serial]['hwid']

  def GetVPD(self, serial):
    """See help(ShopFloorBase.GetVPD)"""
    logging.debug('GetVPD(%s)', serial)
    self._CheckSerialNumber(serial)

    self._AppendStatus(serial, 'GetVPD')
    return self.data_store[serial]['vpd']

  def UploadReport(self, serial, report_blob):
    """See help(ShopFloorBase.UploadReport)"""
    logging.debug('UploadReport(%s, [%s])', serial, len(report_blob))
    self._CheckSerialNumber(serial)
    self.data_store[serial]['reports'].append(report_blob)
    self._AppendStatus(serial, 'UploadReport')

  def Finalize(self, serial):
    """See help(ShopFloorBase.Finalize)"""
    logging.debug('Finalize(%s)', serial)
    self._CheckSerialNumber(serial)
    self._AppendStatus(serial, 'Finalize')


def _CreateSampleDatabase():
  """Returns sample database for shop floor system."""
  # The sample database is a dictionary using serial number as keys, and device
  # records (in dictionary) as values. Each record has following items:
  #  - 'hwid': a HWID string for GetHWID.
  #  - 'vpd': a VPD structure (see the description in ShopFloorBase.GetVPD).
  #  - 'reports': a list of received reports (from UploadReport).
  #  - 'status': a list of status update strings (for Finalize).
  _SAMPLE_HWIDS = ('TEST HWID A-A 4413',
                   'TEST HWID A-B 0951',
                   'TEST HWID2 A-A 3077',
                   'TEST HWID2 A-B 7631')
  # See gooftool/gft_vpd.py for mandatory fields.
  _SAMPLE_VPDS = ({'ro': {'keyboard_layout': 'xkb:us::eng',
                          'initial_locale': 'en-US',
                          'initial_timezone': 'America/Los_Angeles'},
                   'rw': {}},
                  {'ro': {'keyboard_layout': 'xkb:de::ger',
                          'initial_locale': 'de-DE',
                          # Note: Amsterdam is not a German city, but currently
                          # we use it for all UTC+1 regions. See test
                          # factory_SelectRegion for more information.
                          'initial_timezone': 'Europe/Amsterdam'},
                   'rw': {}})

  sample_database = {}
  # Valid serial numbers in sample: 0100 ~ 0199.
  _SKU_START = 100
  _SKU_COUNT = 100
  _SKU_GROUP_SIZE = _SKU_COUNT / len(_SAMPLE_HWIDS)

  for i in xrange(_SKU_COUNT):
    sku_index = int(i / _SKU_GROUP_SIZE)
    data = {}
    serial_number = '%04d' % (_SKU_START + i)
    data['hwid'] = _SAMPLE_HWIDS[sku_index]
    data['vpd'] = copy.deepcopy(_SAMPLE_VPDS[sku_index % len(_SAMPLE_VPDS)])
    # wifi_mac_addr is a sample VPD - not a mandatory field.
    data['vpd']['rw']['wifi_mac_addr'] = (
        '0b:ad:f0:0d:01:%02x' % ((_SKU_START + i) % 0x100))
    data['reports'] = []
    data['status'] = []
    sample_database[serial_number] = data
  return sample_database
