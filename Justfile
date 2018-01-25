#!/usr/bin/env bash

if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then #If being sourced
  set -euE
fi

JUST_PROJECT_PREFIX=VSI_COMMON
source "$(cd "$(dirname "${BASH_SOURCE[0]}")"; pwd)/wrap"
cd "$(\dirname "${BASH_SOURCE[0]}")"

source "${VSI_COMMON_DIR}/linux/just_robodoc_functions.bsh"

function caseify()
{
  local just_arg=$1
  shift 1
  case ${just_arg} in
    test) # Run unit and integration tests
      "${VSI_COMMON_DIR}/tests/run_tests.bsh" ${@+"${@}"}
      extra_args=$#
      ;;
    test_darling) # Run unit and integration tests using darline
        (
          cd "${VSI_COMMON_DIR}"
          darling shell ./tests/run_tests.bsh ${@+"${@}"}
        )
        extra_args=$#
      ;;
    *)
      defaultify "${just_arg}" ${@+"${@}"}
      ;;
  esac
}

if [ "${JUST_IN_SCRIPT-0}" == "0" ]; then caseify ${@+"${@}"};fi
