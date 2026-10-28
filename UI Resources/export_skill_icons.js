// Raster copies for the Pygame UI. The SVGs remain the editable originals.
const fs=require('node:fs');
const path=require('node:path');
const sharp=require('sharp');
const root=path.join(__dirname,'skill-icons');
const onlyNew=process.argv.includes('--only-new');
async function main(){
  let count=0;
  for(const folder of fs.readdirSync(root,{withFileTypes:true}).filter(x=>x.isDirectory())){
    const base=path.join(root,folder.name);
    for(const file of fs.readdirSync(base).filter(x=>x.endsWith('.svg')&&(!onlyNew||x.endsWith('-v2.svg')))){
      for(const size of [64,128,256]){
        const out=path.join(base,`png${size}`);fs.mkdirSync(out,{recursive:true});
        await sharp(path.join(base,file)).resize(size,size).png().toFile(path.join(out,file.replace(/\.svg$/,'.png')));
      }
      count++;
    }
  }
  console.log(`Exported ${count} emblems in three transparent PNG sizes`);
}
main().catch(e=>{console.error(e);process.exitCode=1});
