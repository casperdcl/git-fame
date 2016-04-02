_git_fame()
{
  local cur prv
  cur="${COMP_WORDS[COMP_CWORD]}"
  prv="${COMP_WORDS[COMP_CWORD-1]}"
  case ${COMP_CWORD} in
    1)
      COMPREPLY=($(compgen -cW "fame" ${cur}))
      ;;
    2)
      case ${prv} in
        fame)
          COMPREPLY=($(compgen -W '-h --help -v --version --sort --incl --excl -n --no-regex -s --silent-progress -t --bytype -w --ignore-whitespace -M -C' -- ${cur}))
          ;;
      esac
      ;;
    3)
      case ${prv} in
        "--"sort)
          COMPREPLY=($(compgen -W 'loc commits files' -- ${cur}))
          ;;
      esac
      ;;
    *)
      COMPREPLY=()
      ;;
  esac
}
