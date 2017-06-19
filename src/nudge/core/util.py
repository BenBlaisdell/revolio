import functools
import logging


_log = logging.getLogger(__name__)


def autocommit(func):
    @functools.wraps(func)
    def commit_wrapper(self, *args, **kwargs):
        result = func(self, *args, **kwargs)

        if not hasattr(self, '_db'):
            _log.warning('{} has no _db attribute to commit')
        else:
            self._db.commit()

        return result

    return commit_wrapper
