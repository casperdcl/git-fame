_git_fame()
{
  local cur prv
  cur="${COMP_WORDS[COMP_CWORD]}"
  prv="${COMP_WORDS[COMP_CWORD-1]}"
  case ${COMP_CWORD} in
    1)
      COMPREPLY=($(compgen -W "fame" ${cur}))
      ;;
    *)
      case ${prv} in
        "--sort")
          COMPREPLY=($(compgen -W 'loc commits files' -- ${cur}))
          ;;
        *)
          if [ ${COMP_WORDS[1]} == fame ]; then
            COMPREPLY=($(compgen -dW '-h --help -v --version --cost-time --branch --since --sort --incl --excl -n --no-regex -s --silent-progress -t --bytype -w --ignore-whitespace -M -C --format --manpath --log' -- ${cur}))
          fi
          ;;
      esac
      ;;
  esac
}
