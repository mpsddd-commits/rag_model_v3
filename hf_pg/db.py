"""
Backwards-compatibility wrapper for MariaDB client functions.
Maps original camelCase names to new refactored snake_case functions.
"""
from database.mariadb_client import (
    get_conn,
    find_one,
    find_all,
    save as _save,
    save_many,
    add_key,
    exists as _exists,
    get_page_list,
    sign_up_transaction,
    execute_transaction
)

# Exposing original camelCase names for absolute backward compatibility
getConn = get_conn
findOne = find_one
findAll = find_all
save = _save
saveMany = save_many
addKey = add_key
exists = _exists
getPageList = get_page_list
signUpTransaction = sign_up_transaction
executeTransaction = execute_transaction